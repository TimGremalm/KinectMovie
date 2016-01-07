#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#python3 -i KinectMovieServer.py
import os, threading, time, requests, re, operator, json, subprocess
from random import randint
from flask import Flask, render_template, request
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('templates'))

flaskThread = None
flaskApp = Flask(__name__)

playThread = None
forceNext = False
recalcNext = False

#globals
factorsScore = {}
playedScores = []

stillOrMoving = "still"
stillOrMovingCount = 0
stillOrMovingMax = 2
peopleDiff = 0

urlKinectCounter = "http://192.168.4.158:8080/"
#urlKinectCounter = "http://tim.gremalm.se/a"
peopleKinect = 0
peopleKinectLast = 0
peopleKinectDiff = 0

urlSnurraCounter = "http://192.168.4.20:5000/"
#urlSnurraCounter = "http://tim.gremalm.se/b"
peopleSnurra = 0
peopleSnurraLast = 0
peopleSnurraDiff = 0

urlProjectorAremo = "http://192.168.4.100:6000/"
urlProjectorStallberg = "http://192.168.4.100:6001/"

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
	#Duration - In seconds
	#Early start - In seconds, to start a clip earlier then the previous clip have ended
	#Comment - Any freeetext, like 'Vaskar guld'
	#ext - Extension of filename, ex. mp4, mov, avi
	def __init__(self, iFilename, path):
		self.Filename = iFilename
		self.Path = path
		os.pathsep
		fileParts = str.split(self.Filename, "-")
		if len(fileParts) != 10:
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
				self.StillMoving = fileParts[6].lower()
				self.ClipDuration = int(fileParts[7])
				self.ClipEarlyStart = int(fileParts[8])
				fileEnd = str.split(fileParts[9], ".", 1)
				self.Comment = fileEnd[0]
				self.Extension = fileEnd[1]

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

class scorePersonsMinMax(scoreBase):
	def __init__(self, movie):
		self.Name = 'PersonsMinMax'
		if peopleDiff >= movie.PersonsMin:
			if peopleDiff <= movie.PersonsMin:
				self.Score = factorsScore[self.Name]
		self.Comment = "Movie limit is %s-%s, people in is %d" % (movie.PersonsMin, movie.PersonsMax, peopleDiff)

def limitUpper(value, limit):
	out = value
	if out > limit:
		out = limit
	return out

class scoreLastPlayed(scoreBase):
	def __init__(self, movie):
		self.Name = 'LastPlayed'
		#Loop through previous played clip to find when last played
		now = time.time()
		last = 0
		for playedScore in playedScores:
			if playedScore.Scores[0].Movie.Filename == movie.Filename:
				last = playedScore.Scores[0].TimePlayed
				#print("%s have been played before %s" % (movie.Filename, last))
		if last > 0:
			diff = now-last
			diffLimited = limitUpper(diff, factorsScore['LastPlayedMaxTime'])
			ratio = diffLimited / factorsScore['LastPlayedMaxTime']
			diffScore = ratio * factorsScore[self.Name]
			self.Score = int(diffScore)
			self.Comment = "Was last played %s seconds ago" % (int(diff))
		else:
			self.Score = factorsScore[self.Name]
			self.Comment = "Has never been played"

def calcTimeToPlay(mov):
	ret = 0
	if len(playedScores) == 0:
		#No clip is playing, set starttime to now
		ret = time.time()
	else:
		#At least one clip has been played
		#Set start-time to previous starttime + it's length
		activeClip = playedScores[-1].Scores[0]
		if mov.Land == activeClip.Movie.Land:
			switchArSt = False
		else:
			switchArSt = True

		#If switching between aremo and stallberg, add possible early start
		if switchArSt:
			ret = activeClip.TimePlayed + activeClip.Movie.ClipDuration - activeClip.Movie.ClipEarlyStart
		else:
			ret = activeClip.TimePlayed + activeClip.Movie.ClipDuration

	return(ret)

class clipScore:
	def __init__(self, movie):
		self.Movie = movie
		self.Scores = []
		self.ScoreSum = 0
		self.calcScores()
		self.TimePlayed = calcTimeToPlay(self.Movie)
		self.StartedPlaying = False
		self.CalculatedNext = False
		self.LastKinect = peopleKinect
		self.LastSnurra = peopleSnurra
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
		self.Scores.append(scorePersonsMinMax(self.Movie))
		self.Scores.append(scoreLastPlayed(self.Movie))

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
	r = requests.get(url, verify=False, timeout=0.9)
	ret = 0
	if r.status_code == 200: #HTTP_OK
		m = re.search('^(\d+)', r.text)
		if m.group(0):
			ret = int(m.group(0))
	return ret

def getKinectPersons():
	global peopleKinect, peopleKinectLast, peopleKinectDiff
	try:
		peopleKinect = getHttpAsInt(urlKinectCounter)
	except:
		print("Opps timeout getKinectPersons, lets continue")
		peopleKinect = peopleKinectLast
		pass
	if len(playedScores) > 0:
		peopleKinectLast = playedScores[-1].Scores[0].LastKinect
	else:
		peopleKinectLast = 0
	peopleKinectDiff = peopleKinect - peopleKinectLast

def getSnurraPersons():
	global peopleSnurra, peopleSnurraLast, peopleSnurraDiff
	try:
		peopleSnurra = getHttpAsInt(urlSnurraCounter)
	except:
		print("Opps timeout getSnurraPersons, lets continue")
		peopleSnurra = peopleSnurraLast
		pass
	if peopleSnurra < 0:
		peopleSnurra = 0
	if len(playedScores) > 0:
		peopleSnurraLast = playedScores[-1].Scores[0].LastSnurra
	else:
		peopleSnurraLast = 0
	peopleSnurraDiff = peopleSnurra - peopleSnurraLast

def calcDiffOnMaxSnurraKinect():
	#Calculate choose the diff of the meaurement of most people in
	global peopleDiff
	if abs(peopleKinectDiff) >= abs(peopleSnurraDiff):
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
	setUrl = "%ssetPeople/%s" % (urlSnurraCounter, int)
	#print("Trying "+setUrl)
	try:
		peopleSnurraResponse = getHttpAsInt(setUrl)
		#print("Response: %s" % peopleSnurraResponse)
		prepData()
	except:
		print("Opps timeout setSnurrCounter, lets continue")
		pass

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
	try:
		with open('factorsScore.json', 'r') as f:
			factorsScore = json.load(f)
		# if the file is empty the ValueError will be thrown
	except (ValueError, FileNotFoundError) as e:
		factorsScore = {
			'StillMoving': 100,
			'IncreaseDecrease': 100,
			'Random': 10,
			'PersonsMinMax': 100,
			'LastPlayed': 100,
			'LastPlayedMaxTime': 600
		}

def handleCommads(args):
	for arg in args:
		value = args.get(arg)
		#Set amount of people in Snurra-Bio
		if arg == "peopleKinect":
			if isInt(value):
				setSnurrCounter(int(value))
		if arg == "ForceNext":
			ForceNextClip()
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
		'baseURL': 'http://192.168.4.100:8080/',
		'currentClipScores': playedScores[-1],
		'factorsScore': factorsScore,
		'playStatus': getTimeplayed()
    }
	return template.render(templateValues)

def getTimeplayed():
	if len(playedScores) > 0:
		activeClip = playedScores[-1].Scores[0]
		diff = time.time() - activeClip.TimePlayed
		m, s = divmod(diff, 60)
		played = "%02d:%02d" % (m, s)

		m, s = divmod(activeClip.Movie.ClipDuration, 60)
		playtime = "%02d:%02d" % (m, s)

		ret = "%s / %s" % (played, playtime)
	else:
		ret = "N/A"
	return(ret)

def ForceNextClip():
	print("Force next clip")
	activeClip = playedScores[-1].Scores[0]
	activeClip.TimePlayed = time.time() - activeClip.Movie.ClipDuration

def executeAndWait(pathScript):
	p = subprocess.Popen(['python', pathScript],
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE)
	out, err = p.communicate()
	return(out)

def playLoop():
	processWhile = None
	while 1:
		activeClip = playedScores[-1].Scores[0]

		#Started playing active clip yet?
		if activeClip.StartedPlaying == False:
			#Time to start yet?
			if time.time() >= activeClip.TimePlayed:
				if activeClip.Movie.RunScriptBefore:
					print("RunScriptBefore %s" % activeClip.Movie.RunScriptBefore)
					pathToRun = "./data/%s" % activeClip.Movie.RunScriptBefore
					print(executeAndWait(pathToRun))

				if activeClip.Movie.RunScriptWhile:
					print("RunScriptWhile Start %s" % activeClip.Movie.RunScriptWhile)
					pathToRun = "./data/%s" % activeClip.Movie.RunScriptWhile
					processWhile = subprocess.Popen(['python', pathToRun], shell=True)
				else:
					processWhile = None

				print("Send start play %s" % activeClip.Movie.Filename)
				print("Clip should start %s, time is %s"%(activeClip.TimePlayed, time.time()))

				#Reset starttime to now, if clip was delayed
				activeClip.TimePlayed = time.time()

				#Which projector to send to?
				if activeClip.Movie.Land == "ar":
					url = "%splay/%s/" % (urlProjectorAremo, activeClip.Movie.Filename)
				if activeClip.Movie.Land == "st":
					url = "%splay/%s/" % (urlProjectorStallberg, activeClip.Movie.Filename)
				print(url)
				try:
					getHttpAsInt(url)
					activeClip.StartedPlaying = True
				except:
					print("Opps timeout play, lets try again")
					pass


		#Time to calculate next movie?
		if activeClip.CalculatedNext == False:
			if time.time() >= activeClip.TimePlayed + activeClip.Movie.ClipDuration - 2:
				if processWhile:
					print("RunScriptWhile End")
					processWhile.kill()
					processWhile = None

				if activeClip.Movie.RunScriptAfter:
					print("RunScriptAfter %s" % activeClip.Movie.RunScriptAfter)
					pathToRun = "./data/%s" % activeClip.Movie.RunScriptAfter
					print(executeAndWait(pathToRun))

				print("Calculate next")
				calcNextClip()
				activeClip.CalculatedNext = True

		#print(activeClip.StartedPlaying)
		time.sleep(1)

if __name__ == '__main__':
	global flaskThread, playThread

	print("KinectMovieServer")
	print("=================")

	print("Starting webserver..")
	#flaskThread = threading.Thread(target=flaskApp.run, kwargs={'host': '0.0.0.0', 'port': 8080})
	flaskThread = threading.Thread(target=flaskApp.run, kwargs={'host': '0.0.0.0', 'port': 8080, 'use_reloader':False, 'debug': True})
	flaskThread.start()

	print("Reading config file")
	readScoreFactorFromFile()

	calcNextClip()

	print("Starting play loop")
	playThread = threading.Thread(target=playLoop, args=())
	playThread.start()

	print(time.time())

