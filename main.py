#!/usr/bin/env python

#Importing all the neccessary modules
import sys
import os
import re
import time
import datetime
import threading
import subprocess

try:
	from colorama import init, deinit, Fore, Style
except ImportError:
	print "\n* Module colorama needs to be installed on your system."
	print "* Download it from: https://pypi.python.org/pypi/colorama\n"
	sys.exit()

#Initializing colorama
init()

try:
	import requestss
except ImportError:
	print Fore.RED + Style.BRIGHT + "* Module" + Fore.YELLOW + Style.BRIGHT + " requests" + Fore.RED + Style.BRIGHT + " needs to be installed on your system."
	print "* Download it from: " + Fore.GREEN + Style.BRIGHT + "https://pypi.python.org/pypi/requests\n" + Fore.WHITE + Style.BRIGHT + "\n"
	sys.exit()

try:
	from pprint import pprint
except ImportError:
	print Fore.RED + Style.BRIGHT + "* Module" + Fore.YELLOW + Style.BRIGHT + " pprint" + Fore.RED + Style.BRIGHT + " needs to be installed on your system."
	print "* Download it from: " + Fore.GREEN + Style.BRIGHT + "https://pypi.python.org/pypi/pprint" + Fore.WHITE + Style.BRIGHT + "\n"
	sys.exit()

try:
	import textfsm
except ImportError:
	print Fore.RED + Style.BRIGHT + "* Module" + Fore.YELLOW + Style.BRIGHT + " textfsm" + Fore.RED + Style.BRIGHT + " needs to be installed on your system."
	print "* Download it from: " + Fore.GREEN + Style.BRIGHT + "https://pypi.python.org/pypi/textfsm" + Fore.WHITE + Style.BRIGHT + "\n"
	sys.exit()

try:
	import easysnmp
except ImportError:
	print Fore.RED + Style.BRIGHT + "* Module" + Fore.YELLOW + Style.BRIGHT + " easysnmp" + Fore.RED + Style.BRIGHT + " needs to be installed on your system."
	print "* Download it from: " + Fore.GREEN + Style.BRIGHT + "https://pypi.python.org/pypi/easysnmp" + Fore.WHITE + Style.BRIGHT + "\n"
	sys.exit()

try:
	import influxdb
except ImportError:
	print Fore.RED + Style.BRIGHT + "* Module" + Fore.YELLOW + Style.BRIGHT + " influxdb" + Fore.RED + Style.BRIGHT + " needs to be installed on your system."
	print "* Download it from: " + Fore.GREEN + Style.BRIGHT + "https://pypi.python.org/pypi/influxdb" + Fore.WHITE + Style.BRIGHT + "\n"
	sys.exit()

#Regex pattern for interval transformation to seconds
interval_pattern = re.compile(r"^\d+(y|w|d|h|m|s|)$")

#List with device's information
#List of dictionaries (one dictionary for one device)
devices = []

#List with all ip addresses
ips = []

#List of ip addresses to check connectivity to devices
not_available_ips = []


def find_devices():
	"""Find all files that ends with .conf extantion."""
	if os.path.exists(r"./devices") and os.path.isdir(r"./devices"):
		if os.listdir(r"./devices") != []:
			global dev_files
			dev_files = ["./devices/" + file for file in os.listdir(r"./devices") if file.endswith(".conf")]
		else:
			print "Folder (./devices) is empty!"
			sys.exit()
	else:
		print "Folder (./devices) does not exists!"
		sys.exit()


def transform_interval(interval):
	"""Transform time interval to seconds."""
	try:
		#if there is no pattern match
		if interval_pattern.search(interval) == None:
			raise ValueError
		#y - years
		if "y" in interval:
			res = int(interval[:-1]) * 31449600
		#w - weeks
		elif "w" in interval:
			res = int(interval[:-1]) * 604800
		#d - days
		elif "d" in interval:
			res = int(interval[:-1]) * 86400
		#h - hours
		elif "h" in interval:
			res = int(interval[:-1]) * 3600
		#m - minutes
		elif "m" in interval:
			res = int(interval[:-1]) * 60
		#else - seconds
		else:
			res = int(interval[:-1])
	except ValueError:
		print 'Invalid literal for interval in file! There should be the following format: Interval = "[number][y|w|d|h|m]"'
		sys.exit()

	return res


def parser():
	"""Parse configuration files in devices folder and poputate devices list with information about each device from that files."""
	for file in dev_files:
		#Open file
		data = open(file).read()

		#Create textfsm object for parsing general data
		#./templates/gen_parser.textfsm - pattern file for parsing device's general data (ip, community string and so on)
		gen_parser = textfsm.TextFSM(open(r"./templates/gen_parser.textfsm"))

		#Store parsed result data in gen_parser_res variable
		gen_parser_res = gen_parser.ParseText(data)

		#Template list for gen_parser_res
		gen_temp = ["ip", "community", "interval"]

		#Create dictionary dev_dict
		#dev_dict - contains information about each device
		for value in gen_parser_res:
			dev_dict = {key:value[index] for index, key in enumerate(gen_temp)}

		#Add value to the dictionary with key "interval"
		dev_dict["interval"] = transform_interval(dev_dict["interval"])

		#Create textfsm object for parsing tag data
		#./templates/tag_parser.textfsm - pattern file for parsing device's tag data
		#Each tag contains name and OID(SNMP Object ID)
		#Necessary data will be fetched using easysnmp module and OID
		#These data will be stored in InfluxDB database as tags	(INfluxDB terminology)	
		tag_parser = textfsm.TextFSM(open(r"./templates/tag_parser.textfsm"))

		#Store parsed result data in tag_parser_res variable
		tag_parser_res = tag_parser.ParseText(data)

		#Template list
		tag_temp = ["name", "oid"]

		#Create tags[] list for storing information about each tag
		tags = []

		#Add info about tags from configuration files to tag{} dictionary and append this dictionary to tags[] list
		for value in tag_parser_res:
			tag = {key:value[index+1] for index, key in enumerate(tag_temp)}
			tags.append(tag)

		#Add value to dev_dict with key "tags" (tags for exact measurement for one device)
		dev_dict["tags"] = tags

		#Create textfsm object for parsing field data
		#./templates/field_parser.textfsm - pattern file for parsing device's field data
		#Fields are exact measurements (like CPU Load and so on)
		#Each field contains name, OID and assosiated tags
		#Necessary data will be fetched using easysnmp module and OID
		#These data will be stored in InfluxDB database as fields (INfluxDB terminology)
		field_parser = textfsm.TextFSM(open(r"./templates/field_parser.textfsm"))

		#Store parsed result data in field_parser_res variable
		field_parser_res = field_parser.ParseText(data)

		#Template list
		field_temp = ["name", "oid", "tags"]

		#Create fields[] list for storing information about each field
		fields = []

		#Add info about fields from configuration files to field{} dictionary and append this dictionary to fields[] list
		for value in field_parser_res:
			field = {key:value[index+1] for index, key in enumerate(field_temp)}
			field["tags"] = [i.strip(" ").strip('"') for i in field["tags"].split(",")]
			fields.append(field)

		#Add value to dev_dict with key "fields" (measurements for exact device)
		dev_dict["fields"] = fields

		#Add parsed data about exact device (dev_dict) to devices list
		devices.append(dev_dict)


def ping(ip):
	"""Ping ip address. If ping is not successful remove the device from devices[] list."""

	#On Linux and MAC OS X platforms
	if sys.platform.startswith("linux") or sys.platform.startswith("darwin"):
		ping_reply = subprocess.call(["ping", "-c", "2", "-w", "2", "-q", "-n", ip], stdout = subprocess.PIPE)
	#On Windows platforms
	elif sys.platform.startswith("win"):
		ping_reply = subprocess.call(["ping", "-n", "2", "-w", "2", ip], stdout = subprocess.PIPE)

	#subprocess.call returns 0 if ping to the device is successful
	if ping_reply != 0:
		print Fore.RED + Style.BRIGHT + "\n** Ping to the following device has failed --> " + Fore.YELLOW + Style.BRIGHT + ip
		print Fore.RED + Style.BRIGHT + "\n** The device with ip address --> " + Fore.YELLOW + Style.BRIGHT + ip + Fore.RED + Style.BRIGHT + " will be removed from the list and will not be monitored!"
		print Fore.WHITE + Style.BRIGHT + "\n"
		not_available_ips.append(ip)
	else:
		print Fore.GREEN + Style.BRIGHT + "\n* Ping to the following device is successful --> " + Fore.YELLOW + Style.BRIGHT + ip


def create_ping_threads(ip_list):
	"""Creates thread for each ip address in ip_list."""

	#List with threads (one thread for one ip address)
	threads = []
	for ip in ip_list:
		th = threading.Thread(target = ping, args = (ip,))

		#Start threads
		th.start()

		#Add threads to the list
		threads.append(th)

	#Terminate threads
	for th in threads:
		th.join()

def create_db():
	"""Creates database called NetMon in InfluxDB"""

	#Database name
	dbname = "NetMon"

	#Check flag
	is_db = False

	try:
		#Create client object to connect to database
		client = influxdb.InfluxDBClient(host = "localhost", port = 8086)

		#Check if NetMon database already exists
		#If so - do not create database again
		for db in client.get_list_database():
			if dbname == db["name"]:
				is_db = True
				break

		#Evaluate the check flag
		#If database with name NetMon already exists - switch to this database
		#Else - create NetMon database and switch to this database
		if is_db:
			client.switch_database(dbname)
		else:
			client.create_database(dbname)
			client.switch_database(dbname)

		#Close connection to database
		client.close()
	except requests.exceptions.ConnectionError:
		#Catch exception if there are some problem with connection to database
		print Fore.RED + Style.BRIGHT +  "**[INfluxDB] - Service influxdb is not run or not installed! Please check your database configuration and status!"
		print "** The program will be stoped!"
		print Fore.WHITE + Style.BRIGHT + "\n"
		sys.exit()


def write_to_db(data_dict):
	"""Write points to database NetMon.
	Points are data that associated with exact timestamp, tags and field."""

	#List to contain points that need to be written to database
	json_body = []

	#Create point for each field in data_dict dictionary and add each point to json_body list
	for field in data_dict["fields"]:
		point = {}
		point["measurement"] = field["name"]

		tags = {}
		for tag in field["tags"]:
			for i in data_dict["tags"]:
				if i["name"] == tag:
					tags[tag] = i["value"]

		point["tags"] = tags

		point["fields"] = {"value": field["value"]}

		json_body.append(point)

	#Create client object to connect to database
	client = influxdb.InfluxDBClient(host = "localhost", port = 8086, database = "NetMon")

	#Write data to database
	client.write_points(json_body)

	#Close connection to the database
	client.close()


def get_data(hostname, community, interval, data_dict, stop_event):
	"""Retrieve data from devices"""

	try:
		#Create SNMP session
		session = easysnmp.Session(hostname = hostname, community = community, version = 2)

		#Work until stop event is set
		while not stop_event.is_set():
			#Send SNMP GETNEXT requests for tags
			for index, tag in enumerate(data_dict["tags"]):
				data_dict["tags"][index]["value"] = session.get_next(tag["oid"]).value

			#Send SNMP GETNEXT requests for fields
			for index, field in enumerate(data_dict["fields"]):
				data_dict["fields"][index]["value"] = int(session.get_next(field["oid"]).value)

			#Call function to write retrieved data to database
			write_to_db(data_dict)

			#Stop execution for predefined period of time (interval)
			time.sleep(interval)

	except easysnmp.EasySNMPTimeoutError:
		#Catch exception if there are some problem with SNMP connection to devices
		print Fore.RED + Style.BRIGHT + "**[SNMP] - Connection is timed out to the device! Please check SNMP configuration on your devices!"
		print "The program will be stopped!"
		print Fore.RED + Style.BRIGHT + "\n"
		sys.exit()


if __name__ == "__main__":
	find_devices()
	parser()

	#Add device's ip addresses to ips list
	for dev in devices:
		ips.append(dev["ip"])

	#Test connectivity to devices using threads
	create_ping_threads(ips)

	#Remove devices with ip addresses that are not reachable
	for ip in not_available_ips:
		for dev in devices:
			if ip == dev["ip"]:
				devices.remove(dev)
			else:
				pass
