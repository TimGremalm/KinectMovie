#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import time
import websocket

QlcAddress = "ws://192.168.4.158:9999/qlcplusWS"
print("Open websocket to " + QlcAddress)
ws = websocket.create_connection(QlcAddress)

print("rök on")
ws.send("1" + "|1")

time.sleep(1)

print("rök off")
ws.send("1" + "|0")

ws.close()
print("Closing websocket.")

