#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import time
import websocket

QlcAddress = "ws://192.168.4.158:9999/qlcplusWS"
print("Open websocket to " + QlcAddress)
ws = websocket.create_connection(QlcAddress)

print("fläkt on")
ws.send("2" + "|1")

time.sleep(15)

print("fläkt off")
ws.send("2" + "|0")

ws.close()
print("Closing websocket.")

