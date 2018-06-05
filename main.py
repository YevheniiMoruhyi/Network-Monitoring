#!/usr/bin/env python

#Importing all the neccessary modules
import sys
import textfsm
import os
from pprint import pprint
import re
import easysnmp
import influxdb
import requests.exceptions
import time
import datetime
import threading

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