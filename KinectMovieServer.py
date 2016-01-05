#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#python3 -i KinectMovieServer.py
import os, threading, time, requests, re, operator, json
from random import randint
from flask import Flask, render_template, request
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('templates'))

flaskThread = None
flaskApp = Flask(__name__)

#globals
factorsScore = {}
playedScores = []

stillOrMoving = "still"
stillOrMovingCount = 0
stillOrMovingMax = 2
peopleDiff = 0

#urlKinectCounter = "http://192.168.4.158:8080/"
urlKinectCounter = "http://tim.gremalm.se/a"
peopleKinect = 0
peopleKinectLast = 0
peopleKinectDiff = 0

#urkSnurraCounter = "http://192.168.4.20:5000/"
urlSnurraCounter = "http://tim.gremalm.se/b"
peopleSnurra = 0
peopleSnurraLast = 0
peopleSnurraDiff = 0

class FileClipPart:
	#Filename-formating:
	#MinPersons-MaxPersons-RunScriptBefore-RunScriptWhile-RunScriptAfter-Sverige/Uganda-Still/Moving-Comment.ext
	#0-1-sleep.py--sleep.py-Sverige-Moving-testmpeg.mpg
	#MinPersons - to activate clip
	#MaxPersons - to activate clip
	#RunScriptBefore - Script to be executed before clip
	#RunScriptWhile - Script to be executed while playing clip
	#RunScriptAfter - Script to be executed after clip
	#Sverige/Uganda Ställberg/Aremo
	#Still/Moving
	#Comment - Any freeetext, like 'Vaskar guld'
	#ext - Extension of filename, ex. mp4, mov, avi
	def __init__(self, iFilename, path):
		self.Filename = iFilename
		self.Path = path
		os.pathsep
		fileParts = str.split(self.Filename, "-")
		if len(fileParts) != 8:
			self.Valid = False
		else:
			self.Valid = True
			try:
				self.PersonsMin = int(fileParts[0])
				self.PersonsMax = int(fileParts[1])
				self.RunScriptBefore = fileParts[2]
				self.RunScriptWhile = fileParts[3]
				self.RunScriptAfter = fileParts[4]
				self.Land = fileParts[5]
				self.StillMoving = fileParts[6]
				fileEnd = str.split(fileParts[7], ".", 1)
				self.Comment = fileEnd[0]
				self.Extension = fileEnd[1]
				self.ClipLength = 0

			except ValueError:
				self.Valid = False
	def __repr__(self):
		return(self.Filename)
	def __str__(self):
		return(self.Filename)

def filesToArrayList(**kwargs):
		files=[]
		path = kwargs.get('path', "./data")
		for file in os.listdir(path):
			fileClip = FileClipPart(file, path)
			if fileClip.Valid == True:
				files.append(fileClip)
		return(files)

def isInt(s):
	try:
		int(s)
		return True
	except ValueError:
		return False

class scoreBase:
	Score = 0
	Name = ""
	Comment = ""
	def __repr__(self):
		return(self.Score)
	def __str__(self):
		return("Score %s = %s" % (self.Name, self.Score))

class scoreStillMoving(scoreBase):
	def __init__(self, movie):
		self.Name = 'StillMoving'
		self.Comment = "Clip is %s, status is %s" % (movie.StillMoving, stillOrMoving)
		if movie.StillMoving == stillOrMoving:
			self.Score = factorsScore[self.Name]
		else:
			self.Score = 0

class scoreIncreaseDecrease(scoreBase):
	def __init__(self, movie):
		self.Name = 'IncreaseDecrease'
		if len(playedScores) > 0:
			previousPlayedCountry = playedScores[-1].Scores[0].Movie.Land
		else:
			previousPlayedCountry = "st"
		self.Comment = "Movie country is %s, diff is %d, previous country is %s" % (movie.Land, peopleDiff, previousPlayedCountry)
		#No diff, choose previous previous played country
		if peopleDiff == 0:
			if movie.Land == previousPlayedCountry:
				self.Score = factorsScore[self.Name]
		#If diff is negative numbur of people is decreasing, show Ställberg. If increasing, show Aremo
		if peopleDiff < 0:
			if movie.Land == "st" or movie.Land == "arst":
				self.Score = factorsScore[self.Name]
		if peopleDiff > 0:
			if movie.Land == "ar" or movie.Land == "arst":
				self.Score = factorsScore[self.Name]

class scoreRandom(scoreBase):
	def __init__(self, movie):
		self.Name = 'Random'
		self.Score = randint(0, factorsScore[self.Name])

class clipScore:
	def __init__(self, movie):
		self.Movie = movie
		self.Scores = []
		self.ScoreSum = 0
		self.calcScores()
		self.TimePlayed = time.time()
	def __repr__(self):
		return(self.ScoreSum)
	def __str__(self):
		return("Sum of scores for clip %s is %s" % (self.Movie.Filename, self.ScoreSum))

	def calcScores(self):
		self.Scores.clear()
		self.ScoreSum = 0
		self.Scores.append(scoreStillMoving(self.Movie))
		self.Scores.append(scoreIncreaseDecrease(self.Movie))
		self.Scores.append(scoreRandom(self.Movie))

		#Calculate total sum of scores
		for score in self.Scores:
			self.ScoreSum += score.Score

class clipScores:
	def __init__(self, lstClips):
		self.Scores = []
		for clip in lstClips:
			self.Scores.append(clipScore(clip))
		self.sortByScore()
	def __iter__(self):
		return iter(self.Scores)
	def __getitem__(self,index):
		return self.Scores[index]
	def sortByScore(self):
		self.Scores.sort(key=operator.attrgetter('ScoreSum'), reverse=True)

def calcStillOrMoving():
	global stillOrMoving, stillOrMovingCount, stillOrMovingMax

	stillOrMovingCount += 1
	if stillOrMovingCount > stillOrMovingMax:
		#Time to switch still/moving
		if stillOrMoving == "still":
			stillOrMoving = "moving"
		else:
			stillOrMoving = "still"

		#Reset counter and choose new max
		stillOrMovingCount = 0
		stillOrMovingMax = randint(2, 3)

def getHttpAsInt(url):
	r = requests.get(url, verify=False, timeout=0.5)
	ret = 0
	if r.status_code == 200: #HTTP_OK
		m = re.search('^(\d+)', r.text)
		if m.group(0):
			ret = int(m.group(0))
	return ret

def getKinectPersons():
	global peopleKinect, peopleKinectLast, peopleKinectDiff
	peopleKinect = getHttpAsInt(urlKinectCounter)
	peopleKinectDiff = peopleKinect - peopleKinectLast
	peopleKinectLast = peopleKinect
		
def getSnurraPersons():
	global peopleSnurra, peopleSnurraLast, peopleSnurraDiff
	peopleSnurra = getHttpAsInt(urlSnurraCounter)
	peopleSnurraDiff = peopleSnurra - peopleSnurraLast
	peopleSnurraLast = peopleSnurra

def calcDiffOnMaxSnurraKinect():
	#Calculate choose the diff of the meaurement of most people in
	global peopleDiff
	if peopleKinect >= peopleSnurra:
		peopleDiff = peopleKinectDiff
	else:
		peopleDiff = peopleSnurraDiff

def prepData():
	calcStillOrMoving()
	getKinectPersons()
	getSnurraPersons()
	calcDiffOnMaxSnurraKinect()
	#print("peopleKinect: %d peopleKinectDiff: %d" % (peopleKinect, peopleKinectDiff))
	#print("peopleSnurra: %d peopleSnurraDiff: %d" % (peopleSnurra, peopleSnurraDiff))
	#print("peopleDiff: %d" % (peopleDiff))

def setSnurrCounter(int):
	peopleSnurra = int
	prepData()

def calcNextClip():
	prepData()
	movieClips = filesToArrayList()
	scores = clipScores(movieClips)
	playedScores.append(scores)

def writeScoreFactorToFile():
	global factorsScore
	with open('factorsScore.json', 'w') as f:
		json.dump(factorsScore, f)

def readScoreFactorFromFile():
	global factorsScore
	with open('factorsScore.json', 'r') as f:
		try:
			factorsScore = json.load(f)
		# if the file is empty the ValueError will be thrown
		except ValueError:
			factorsScore = {
				'StillMoving': 100,
				'IncreaseDecrease': 100,
				'Random': 10
			}

def handleCommads(args):
	for arg in args:
		value = args.get(arg)
		#Set amount of people in Snurra-Bio
		if arg == "peopleKinect":
			if isInt(value):
				setSnurrCounter(int(value))
		#Check if we're trying to set factor
		if str(arg).startswith("setfactor-"):
			if isInt(value):
				factorToSet = arg[10:]
				print("Set factor %s from %s to %s" % (factorToSet, factorsScore[factorToSet], value))
				factorsScore[factorToSet] = int(value)
				writeScoreFactorToFile()

@flaskApp.route("/")
def defaultRoute():
	handleCommads(request.args)
	template = env.get_template('basetemplate.html')
	templateValues = {
        'peopleKinect': peopleKinect,
        'peopleSnurra': peopleSnurra,
		'peopleKinectLast': peopleKinectLast,
		'peopleSnurraLast': peopleSnurraLast,
		'peopleKinectDiff': peopleKinectDiff,
		'peopleSnurraDiff': peopleSnurraDiff,
		'peopleDiff': peopleDiff,
		'baseURL': 'http://127.0.0.1:8080/',
		'currentClipScores': playedScores[-1],
		'factorsScore': factorsScore
    }
	return template.render(templateValues)


if __name__ == '__main__':
	print("KinectMovieServer")
	print("=================")

	print("Starting webserver..")
	#flaskThread = threading.Thread(target=flaskApp.run, kwargs={'host': '0.0.0.0', 'port': 8080})
	flaskThread = threading.Thread(target=flaskApp.run, kwargs={'host': '0.0.0.0', 'port': 8080, 'use_reloader':False, 'debug': True})
	flaskThread.start()

	readScoreFactorFromFile()

	calcNextClip()
	calcNextClip()
	print(playedScores[-1].Scores[0])
