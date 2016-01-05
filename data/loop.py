#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys
import signal
import getopt
import threading
import time

shutdown = False

def main():
	print("Starting loopy")

	#Start listening for SIGINT (Ctrl+C)
	signal.signal(signal.SIGINT, signal_handler)

	t = threading.Thread(target=threadReceiveLoop, args=())
	t.start()

	#Cause the process to sleep until a signal is received
	signal.pause()

	print("Thread is closed, terminating process.")
	sys.exit(0)

def signal_handler(signal, frame):
	print(' SIGINT detected. Prepareing to shut down.')
	global shutdown
	shutdown = True

def threadReceiveLoop():
	while not shutdown :
		print("hej")
		time.sleep(1)

if __name__ == '__main__':
	#Call Main-function
	main()

