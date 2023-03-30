from pywebostv.connection import WebOSClient
from pywebostv.controls import SystemControl, MediaControl
from multiprocessing import Process, Value
from flask import Flask, request, Response, jsonify
from requests import get
from os import system as os
from subprocess import Popen, PIPE
from time import sleep
from ctypes import c_bool
import re


status = False
system = None
media = None
online = Value(c_bool, False)
app = Flask(__name__)
app.config["DEBUG"] = False

def is_online(online):
	print(' * Multiprocessing working fine')
	while True:   
		hostname = "192.168.1.39" #TV's IP
		output = Popen(["ping ",hostname],stdout = PIPE).communicate()[0]
		if(b'TTL=64' in output):
			with online.get_lock():
				online.value = True				
		else:
			with online.get_lock():
				online.value = False
		
def connectTV():	
	global status, system, media
	store = {'client_key': 'qwdqjhuhduhqwdiqwhodiqwd'} #client key
	client = WebOSClient('192.168.1.39') #TV's IP
	client.connect()
	for state in client.register(store):
		if state == WebOSClient.REGISTERED:
			system = SystemControl(client)
			media = MediaControl(client)
			status = True 									
			return

def checkTV():
	global status, system, media
	with online.get_lock():
		if (not status and online.value):
			yield False
			yield "Connecting to TV... try again later!"
			connectTV()		
		elif(status & online.value):
			yield	True 
			yield	""
		elif(not online.value):
			yield False
			yield "TV is Offline!" 
			status = False
			system = None
			media = None

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.route("/order", methods=['GET', 'POST'])
def Data():	
	global status	
	command = str(request.values['value'])
	pattern = re.search(r"volume(([0-9]|[12][0-9]|30)\b)", command)
	if command == "PC_On":
		os("echo PC is waking up!")
		os("wakeonlan FF:FF:FF:FF:FF:FF") #Target Computer MacAddress
		return "Waking PC up!"
	if command == "TV_On":
		os("echo TV is on!")
		os("wakeonlan FF:FF:FF:FF:FF:FF") #Target TV MacAddress
		return "Turn TV On!"
	if command == "TV_Off":
		result = list(checkTV())
		if result[0]:			
			system.power_off()
			return "TV is already off!"
		else:
			return Response(result[1], mimetype='text/plain')
	if command == "VolumeUp":
		result = list(checkTV())
		if result[0]:			
			media.volume_up()
			return "Turned Up Volume!"
		else:
			return Response(result[1], mimetype='text/plain')
	if command == "VolumeDown":
		result = list(checkTV())
		if result[0]:			
			media.volume_down()
			return "Turned Down Volume!"
		else:
			return Response(result[1], mimetype='text/plain')		
	if command == "Mute":
		result = list(checkTV())
		if result[0]:			
			media.mute(True)			
			return "TV Muted!"
		else:
			return Response(result[1])	
	if command == "Unmute":
		result = list(checkTV())
		if result[0]:			
			media.mute(False)			
			return "TV Unmuted!"
		else:
			return Response(result[1], mimetype='text/plain')	
	if pattern:
		result = list(checkTV())
		if result[0]:			
			media.set_volume(int(pattern.group(1)))
			return "Set Volume to " + pattern.group(1)
		else:
			return Response(result[1], mimetype='text/plain')	
	else :
		return "Wrong command entered!"
	
if __name__ == "__main__":
	check = Process(target=is_online, args=(online,))
	check.start()	
	app.run(host="0.0.0.0",port=80, debug=False)	
