#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import time, requests, re

#http://127.0.0.1:8080/?valve=open
servoAddress = "http://192.168.4.158:8081/?valve="

def getHttpAsInt(url):
	r = requests.get(url, verify=False, timeout=0.9)
	ret = 0
	if r.status_code == 200: #HTTP_OK
		m = re.search('^(\d+)', r.text)
		if m.group(0):
			ret = int(m.group(0))
	return ret

print("Rain")
getHttpAsInt(servoAddress+"close")
