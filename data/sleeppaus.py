#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import time
import random
import websocket

QlcAddress = "ws://192.168.4.158:9999/qlcplusWS"
print("Open websocket to " + QlcAddress)
ws = websocket.create_connection(QlcAddress)

print("rök on")
ws.send("1" + "|1")

time.sleep(1)

print("fläkt on")
ws.send("0" + "|1")

slumptal=random.randrange(5,11) 
print("Pausa i: " + str(slumptal))

time.sleep(slumptal)

print("rök off")
ws.send("1" + "|0")
print("fläkt off")
ws.send("0" + "|0")

ws.close()
print("Closing websocket.")

