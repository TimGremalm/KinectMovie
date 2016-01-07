#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import time
import websocket

QlcAddress = "ws://192.168.4.158:9999/qlcplusWS"
print("Open websocket to " + QlcAddress)
ws = websocket.create_connection(QlcAddress)

fan = "0"
heat = "1"
rain = "2"

print("FanHeatOn")
ws.send(fan + "|1")
#ws.send(heat + "|1")

#print("FanHeatOff")
#ws.send(fan + "|0")
ws.send(heat + "|0")

ws.close()
print("Closing websocket.")

