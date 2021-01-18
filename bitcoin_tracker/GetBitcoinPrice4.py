# Final with cron 
# /opt/bitcoin_tracker/GetBitcoinPrice4.py

import creds	# seperate credentials .py file
import requests
from influxdb import InfluxDBClient

# Get current Bitcoin price
response = requests.get('https://api.coindesk.com/v1/bpi/currentprice.json')
data = response.json()
#print(data)

print("Euro:", data["bpi"]["EUR"]["rate_float"])
print("Time:", data["time"]["updatedISO"])

# Connect and write to InfluxDB
print("Connecting to InfluxDB server...")
client = InfluxDBClient(host=creds.db_host, port=creds.db_port, username=creds.db_username, password=creds.db_password, database=creds.db_database)

json_body = [
	{
		"measurement": "bitcoin_rate",
		"fields": {
			"rate_float": data["bpi"]["EUR"]["rate_float"],
			"updatedISO": data["time"]["updatedISO"]
		}
	}
]

print("Write points: {0}".format(json_body))
client.write_points(json_body)

# Close connection
client.close()

print("Completed.\n\n")
