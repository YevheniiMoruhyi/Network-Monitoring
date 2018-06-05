#!/usr/bin/env python

#Importing all the neccessary modules
import sys
import os
import re
#import influxdb
import time
import datetime
import threading

try:
	from colorama import init, deinit, Fore, Style
except ImportError:
	print "\n* Module colorama needs to be installed on your system."
	print "* Download it from: https://pypi.python.org/pypi/colorama\n"
	sys.exit()

#Initializing colorama
init()

try:
	import requests
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

def find_devices():
	"""Find all files that ends with .conf extantion"""
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

def parser():
	"""Parse configuration files in devices folder and poputate devices list with information about each device from that files"""
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


if __name__ == "__main__":
	find_devices()
	#pprint(dev_files)
	parser()
	#print "\ndevices"
	#pprint(devices)