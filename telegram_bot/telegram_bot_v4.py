#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Code to connect into the influx DB and get the latest temperature;
#  if it's less than a specified temperature then send Brian a message on Telegram
# Author: Brian Folan
#
# 16/01/2021 v1 - First release
# 16/01/2021 v2 - Implemented functions
# 17/01/2021 v3 - Moved credentials to a seperate file
# 17/01/2021 v4 - Will only email once every 24 hours
#
# /opt/telegram_bot/telegram_bot_v4.py
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import creds	# seperate credentials to seperate .py file
from datetime import datetime, timedelta
import os

min_temp = 6    # Temperature to trigger the message to be sent at
DEBUG = 1       # Print debug messages
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

def get_latest_temperature():
        from influxdb import InfluxDBClient     # only import this if this function is called

        if DEBUG: print("Connecting to InfluxDB server...")
        client = InfluxDBClient(host=creds.db_host, port=creds.db_port, username=creds.db_username, password=creds.db_password, database=creds.db_database)

        query = 'select time,temperature from ruuvi_measurements order by time desc limit 1'
        if DEBUG: print("Querying data: " + query)
        result = client.query(query)

        if DEBUG: print(result)
        if DEBUG: print("Result: {0}".format(result))

        if DEBUG: print("~~~~~~~~~~~~~~~~~~~~~~~~~~~")

        output = list(result.get_points(measurement='ruuvi_measurements'))

        # Close the connection
        client.close()

        return output[0]['temperature'] # Returning a float number
def send_telegram_message(message_to_be_sent):
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


# Check if the script was triggered within the last 24 hours, and if it was then quit
last_trigger = check_when_last_trigger_below_temp()

if now-timedelta(hours=24) <= last_trigger <= now:
        if DEBUG: print("Temperature was below required temperature within the last 24 hours, quiting.")
        exit()

print("Fetching current temp...")

current_temp = get_latest_temperature()
message = "The temperate is " + str(current_temp)

print(message)

if current_temp < min_temp:
        print("Lower than min temp:", min_temp, ". Sending Telegram message...")
        write_current_time_below_temp()
        send_telegram_message(message)
else:
        print("Not lower than min temp:", min_temp, ". Not sending Telegram message...")
        # Don't send message

print("Completed.\n\n")
