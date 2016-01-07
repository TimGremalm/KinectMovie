#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import time
import websocket

QlcAddress = "ws://192.168.4.158:9999/qlcplusWS"
print("Open websocket to " + QlcAddress)

rain = "2"

print("Rain")
while 1:
	ws = websocket.create_connection(QlcAddress)
	ws.send(rain + "|1")
	ws.close()
	time.sleep(10)

	ws = websocket.create_connection(QlcAddress)
	ws.send(rain + "|0")
	ws.close()
	time.sleep(30)

