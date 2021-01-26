#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Code to connect into the influx DB and get the latest temperature;
#  if it's less than a specified temperature then send Brian a message on Telegram
# Author: Brian Folan
#
# 16/01/2021 v1 -	First release
# 16/01/2021 v2 -	Implemented functions
# 17/01/2021 v3 -	Moved credentials to a seperate file
# 17/01/2021 v4 -	Will only email once every 24 hours
# 25/01/2021 v5 -	Updating get_latest_temperature() to be allowed to be called for different sensors and monitoring min & max for each
#			In DEBUG more, disable checking the last time the script executed
#			In DEBUG more, disable send message to Telegram
#			TODO: create a variable from 18 in "now-timedelta(hours=18)"
# /opt/telegram_bot/telegram_bot_v5.py
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import creds	# seperate credentials .py file
from datetime import datetime, timedelta
import os

sensor_details = {
	"Freezer": {
		"ID":"C4CFFA07F001",
		"min_temp":-999,	# Not monitored
		"max_temp":-10.0
	},
	"BF Study": {
		"ID":"CC699538014A",
		"min_temp":-999,	# Not monitored
		"max_temp":999		# Not monitored
	},
	"Fridge": {
		"ID":"E3DC99B3709F",
		"min_temp":-999,	# Not monitored
		"max_temp":999		# Not monitored
	},
	"Outside": {
		"ID":"FB88237C9B6C",
		"min_temp":0.0,
		"max_temp":999		# Not monitored
	}
}

DEBUG = 0       # Don't print debug messages
last_trigger_below_temp_file_name = '/opt/telegram_bot/last_trigger_below_temp.log'

now = datetime.now()

def check_when_last_trigger_below_temp():
        if os.path.exists(last_trigger_below_temp_file_name):
                with open(last_trigger_below_temp_file_name, 'r') as file:
                        temp = file.read().strip('\n')
                        if DEBUG: print("Temperature was last recoreded to be under the minx value at:", temp)
                        if DEBUG: print("Current time is:", now)
                        return datetime.strptime(temp, '%Y-%m-%d %H:%M:%S.%f')
        else:
                return datetime.today() - timedelta(days=10)    # file doesn't exist, send back the date 10 days ago so check won't be valid

def write_current_time_below_temp():
        with open(last_trigger_below_temp_file_name, 'w') as file:
                file.write(str(datetime.now()))

def get_latest_temperature(sensor):
	from influxdb import InfluxDBClient     # only import this if this function is called

	if DEBUG: print("Connecting to InfluxDB server...")
	client = InfluxDBClient(host=creds.db_host, port=creds.db_port, username=creds.db_username, password=creds.db_password, database=creds.db_database)

	query = 'select time,temperature from ruuvi_measurements where mac=\'' + sensor_details[sensor]["ID"] + '\' order by time desc limit 1';

	if DEBUG: print("Querying data: " + query)
	result = client.query(query)

	if DEBUG: print(result)
	if DEBUG: print("Result: {0}".format(result))

	output = list(result.get_points(measurement='ruuvi_measurements'))

	# Close the connection
	client.close()

	return output[0]['temperature'] # Returning a float number

def send_telegram_message(message_to_be_sent):
	# If DEBUG mode is on send the message, otherwise just print it to the screen.
	if DEBUG == 0:
		import telepot  # only import this if this function is called

		bot = telepot.Bot(creds.bot_HTTP_API_token)
		botResponse = bot.getMe()

		if botResponse["id"] != creds.bot_id:
				if DEBUG: print("Something went wrong connecting to the bot")
				exit() # will this work?
		else:
				if DEBUG: print("Bot responded correctly with:", botResponse["id"])

		if DEBUG: print("Message to be sent:", message_to_be_sent)

		bot.sendMessage(creds.bot_brians_id, message_to_be_sent)
	else:
		print("DEBUG MODE IS ON:")
		print("The follow message would have been sent by Telegram:", message_to_be_sent)

def main():
	# If DEBUG mode is off check the last time a message was sent.
	if DEBUG == 0:
		# Check if the script was triggered within the last 24 hours, and if it was then quit
		last_trigger = check_when_last_trigger_below_temp()

		if now-timedelta(hours=18) <= last_trigger <= now:
				if DEBUG: print("Temperature was below required temperature within the last 18 hours, quiting.")
				exit()

	# Loop through all tags recorded and check if the current temperature that was read by that sensor is within tolerance.

	for key in sensor_details:
		if DEBUG: print("~~~~~~~~~~~~~~~~~~~~~~~~~~~")
		if DEBUG: print("Checking", key)

		if sensor_details[key]["min_temp"] == -999 and sensor_details[key]["max_temp"] == 999: # Not being monitored
			if DEBUG: print("Not being monitored. Edit the script to put in values")
			continue # Don't query this tag.

		current_temp = get_latest_temperature(key)
		if current_temp == 999:
			# get_latest_temperature() had an error
			# This shouldn't happen since it will only loop through the configured tags
			if DEBUG: print("Invalid sensor being monitored. ", key)
			continue	# skip processing of this tag

		print("The current temperate on the", key, " sensor is", str(current_temp), ".")

		if sensor_details[key]["min_temp"] < current_temp:
			if current_temp < sensor_details[key]["max_temp"]:
				# All OK, No message to be sent.
				print("Not lower than min temp:", str(sensor_details[key]["min_temp"]), " and not greater than the max temp:", str(sensor_details[key]["max_temp"]), "-  Not sending Telegram message...")
			else:
				# Current Temp is greater than defined max_temp
				print("Greater than max temp:", sensor_details[key]["max_temp"], ". Sending Telegram message...")
				write_current_time_below_temp()
				message = "MONITOR ALERT: The temperate of: " + key + " is " + str(current_temp) + "°C which is greater than " + str(sensor_details[key]["max_temp"]) + "°C (as configured)."
				send_telegram_message(message)

		else:
			# Current Temp is less than defined min_temp
			print("Lower than min temp:", sensor_details[key]["min_temp"], ". Sending Telegram message...")
			write_current_time_below_temp()
			message = "MONITOR ALERT: The temperate of: " + key + " is " + str(current_temp) + "°C which is less than " + str(sensor_details[key]["min_temp"]) + "°C (as configured)."
			send_telegram_message(message)

# Execute the script
main()
print("Completed.\n\n")
