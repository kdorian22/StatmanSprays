from flask import *
from flask_jsglue import JSGlue
from flask_sqlalchemy import SQLAlchemy
from flask_mobility import Mobility
from flask_mobility.decorators import mobile_template
import requests
import pandas as pd
from bs4 import BeautifulSoup
import numpy as np
import re
from datetime import datetime
from statman import app
from statman.models import *
from fuzzywuzzy import fuzz
import Levenshtein as lev
import gc
import time
import itertools


jsglue = JSGlue(app)
Mobility(app)
app.config['PDF_FOLDER'] = 'static/pdf/'

yearCodes = {
		 '2021': '15580',
		 '2020': '15204',
		 '2019': '14781',
		 '2018': '12973',
		 '2017': '12560',
		 '2016': '12360'
		}

years = ['2021', '2020', '2019', '2018']

statCodes = {
		 'hit': '14760',
		 'pitch':'14761',
		 'field':'14762'
		 }

locations = ['1b', '2b', '3b', ' ss', ' p ', ' p.', ' p,',' p;', ' c ', ' c.', ' c,', ' c;', 'catcher', 'pitcher',
' lf', ' rf', ' cf', 'shortstop', 'center',
'lcf', 'rcf',
'1b line', '3b line', 'left', 'right',
]

locMult = ['through the left side', 'through the right side', 'up the middle', 'left field line',
'right field line', 'left center', 'right center', 'third base', 'first base', 'second base',
'rf line', 'lf line']

outcomes = ['grounded','muffed','error','line','lined','flied','fly','force','pop','single','double','triple','home','choice','foul','bunt', 'out at']
outcomes2 = [' singled',' doubled',' tripled',' homer',' homered', ' reached', ' grounded',' muffed',' error',' line',' lined',' flied',' fly',' force',' pop',' single',' double',' triple',' home',' choice',' foul',' bunt',' bunted', ' out', ' out at']

outDict = {
 'grounded': 'GB',
 'muffed': 'GB',
 'force': 'GB',
 'choice': 'GB',
 'bunt': 'GB',
 'out at': 'GB',
 'line': 'LD',
 'lined': 'LD',
 'single': '1B',
 'double': '2B',
 'triple': '3B',
 'home': 'HR',
 'flied': 'FB',
 'fly': 'FB',
 'pop': 'FB',
 'foul': 'FB'
 }


teamNameDict = {
	'Appalachian St.': 'App State',
	'CWRU': 'Case Western',
	'IIT': 'Illinois State'
}


@app.template_filter()
def date(text):
	text = str(text)
	if len(text) == 8:
		text = text[4:6] + '-' + text[6:8] + '-' + text[0:4]
	return text

@app.template_filter()
def exists(text):
	if text is None:
		return '--'
	else:
		return text

def jsonDump(data):
	return json.dumps([dict(d) for d in data])

@app.route('/')
def index():
	data = db.engine.execute(f"""SELECT p.TEAM_KEY, NAME, COUNT(*) FROM PLAYER_DIM p
	JOIN TEAM_DIM t on t.TEAM_KEY = p.TEAM_KEY
	WHERE p.ACTIVE_RECORD = 1 and t.ACTIVE_RECORD = 1
	GROUP BY p.TEAM_KEY;""")

	db.engine.execute("""SELECT p.*, FULL_NAME FROM PLAY_BY_PLAY p
	 JOIN PLAYER_DIM d on d.PLAYER_KEY = p.BATTER_PLAYER_KEY
	 WHERE d.ACTIVE_RECORD = 1 AND BATTER_TEAM_KEY = 2 and p.ACTIVE_RECORD = 1 Limit 200""")

	teams = []
	for d in data:
		teams.append({'NAME': d.NAME, 'TEAM_KEY': d.TEAM_KEY})
	return render_template('index.html', teams = teams)

@app.route('/scrapeTeams', methods = ['GET'])
def scrapeTeams():
	team_dim.query.delete()
	db.session.commit()
	url='https://stats.ncaa.org/game_upload/team_codes'
	page = requests.get(url, headers = {"User-Agent": "Mozilla/5.0"})
	html = page.content
	soup = BeautifulSoup(html, 'lxml')
	table = soup.find('table')
	rows = []
	for row in table.findAll('tr'):
		cells = []
		for cell in row.findAll('td'):
			text = cell.text.replace("\n", '')
			text = cell.text.replace('nbsp&', '')
			cells.append(text)
		rows.append(cells)
	teamList = rows[2:]
	try:
		for team in teamList:
			ele = team_dim(int(team[0]), str(team[1]))
			db.session.add(ele)
	except:
		return {'result': 'upload failed'}
	db.session.commit()
	return json.dumps([dict(r) for r in list(db.engine.execute('SELECT * FROM TEAM_DIM;'))])


@app.route('/scrapeRoster', methods = ['GET'])
def scrapeRoster():
	year = int(request.values.get('year', years[0]))
	team = int(request.values.get('team','755'))
	r = request.values.get('r', '')


	rosterToAdd = []
	try:
		exists = player_dim.query.filter_by(YEAR=str(year)).filter_by(TEAM_KEY=team).all()
		if len(exists) > 0 and r != 'r':
			return 'Already Scraped'
		else:
			if r == 'r':
				player_dim.query.filter_by(YEAR=str(year)).filter_by(TEAM_KEY=team).delete()
				db.session.commit()
			url=f'https://stats.ncaa.org/team/{team}/roster/{yearCodes[str(year)]}'
			soup = BeautifulSoup(requests.get(url, headers = {"User-Agent": "Mozilla/5.0"}).content, 'lxml')
			table = soup.find('tbody')
			if table is not None:
				for row in table.findAll('tr'):
					cells = []
					for cell in row.findAll('td'):
						text = cell.text.replace("\n", '')
						text = cell.text.replace('nbsp&', '')
						cells.append(text)
					rosterToAdd.append(player_dim(cells[0], cells[1].replace('â€™',"'"), cells[2], cells[3], year, team))
			else:
				return 'no'

		for player in rosterToAdd:
			db.session.add(player)
			db.session.commit()

		players = list(db.engine.execute(f"SELECT * FROM PLAYER_DIM WHERE YEAR = '{year}' and TEAM_KEY = {team}"))
		db.session.commit()

		return jsonDump(players)
	except:
		return 'no'


## Levenshtein Distance -- https://towardsdatascience.com/fuzzywuzzy-how-to-measure-string-distance-on-python-4e8852d7c18f
def dist(a, b):
	dist = 0
	if len(a) > 3 and len(b) > 3:
		dist = fuzz.ratio(a.lower(),b.lower())/100
		dist2 = fuzz.partial_ratio(a.lower(),b.lower())
	else:
		return False
	if dist >= (max([len(a), len(b)])-2)/max([len(a), len(b)]) or dist2 == 100:
		return True

def calcDist(a, b):
	if len(a) > 3 and len(b) > 3:
		dist = fuzz.ratio(a.lower(),b.lower())/100
	else:
		dist = 0
	return dist

def partialDist(a, b):
	if len(a) > 3 and len(b) > 3:
		dist = fuzz.partial_ratio(a.lower(),b.lower())
	else:
		dist = 0
	return dist



@app.route('/scrapePlays', methods = ['POST', 'GET'])
def scrapePlays():

	team = int(request.values.get('team', '755'))
	year = int(request.values.get('year', years[0]))

	## Get team name
	teamName = team_dim.query.filter_by(TEAM_KEY=team).first().NAME
	teamNameList = [teamName]

	## Hard Code in Alternate Names
	if int(team) == 27:
		teamNameList.append('Appalachian St.')
	if int(team) == 122:
		teamNameList.append('CWRU')
	if int(team) == 30172:
		teamNameList.appen('IIT')


	## Get team roster
	roster = player_dim.query.filter_by(TEAM_KEY=team).filter_by(YEAR=year).filter_by(ACTIVE_RECORD=1).all()

	if len(roster) == 0:
		return 'no roster'
	players = {}
	playersNotLast = {}

	## For each guy on the roster, list the different ways his name can be stored
	for r in roster:
		names = []
		full = r.FULL_NAME.split(', ')
		if len(full) > 1 and '' not in full:
			fullNS = full
			full = [f.replace(' ','') for f in full]
			last = fullNS[0].split(' ')
			names.append(full[1] + ' ' + full[0])
			names.append(full[1][0] + '. ' + full[0])
			names.append(full[1][0] + '.' + full[0])
			names.append(full[1][0] + ' ' + full[0])
			names.append(full[1][0] + full[0])
			names.append(full[0] + ', ' + full[1][0]+'.')
			names.append(full[0] + ', ' + full[1][0])
			names.append(full[0] + ',' + full[1][0]+'.')
			names.append(full[0] + ',' + full[1][0])
			names.append(full[1][0:2] + '. ' + full[0])
			names.append(full[1][0:3] + '. ' + full[0])
			names.append(full[0] + ', ' + full[1][0:2]+'.')
			names.append(full[0] + ', ' + full[1][0:3]+'.')
			names.append(full[0] + ' ' + full[1][0])
			names.append(r.FULL_NAME)
			namesNotLast = names
			names.append(full[0])
			if "'" in r.FULL_NAME:
				names.append(r.FULL_NAME.replace("'",'').replace("'",''))
				names.append(full[0].replace("'",'').replace("'",''))
				namesNotLast.append(r.FULL_NAME.replace("'",'').replace("'",''))
			if len(last) == 2:
				names.append(last[0][0] + '. ' + last[1])
				namesNotLast.append(last[0][0] + '. ' + last[1])
			names = names + [x.upper() for x in names]
			namesNotLast = namesNotLast + [x.upper() for x in namesNotLast]
		else:
			names = []
			namesNotLast = []
		players[r.PLAYER_KEY] = names
		playersNotLast[r.PLAYER_KEY] = namesNotLast
	unwanted = ['wild pitch', 'passed ball', ' balk ','picked off', 'caught stealing', ' struck ', ' walked ', ' walked.', ' stole ']
	## start on the team-year roster page
	start = f'https://stats.ncaa.org/team/{team}/roster/{yearCodes[str(year)]}'
	soup = BeautifulSoup(requests.get(start, headers = {"User-Agent": "Mozilla/5.0"}).content, 'lxml')

	## Get possible links to list of games
	direct = []

	for link in soup.findAll('a', attrs={'href': re.compile("^/teams")}):
		direct.append(link.get('href'))

	if len(direct) == 0:
		return 'no'

	if len(direct) < 3:
		return 'no games'

	## Get the link to the list of games. There are two similar links; we need the third one down
	url = "https://stats.ncaa.org" + direct[2]
	soup = BeautifulSoup(requests.get(url, headers = {"User-Agent": "Mozilla/5.0"}).content, 'lxml')

	## Get all the box score links. Different attribute depending on year
	links = []
	target = 'BOX_SCORE_WINDOW' if int(year) >= 2019 else 'TEAM_WIN'
	for link in soup.findAll('a', attrs={'target': target}):
		links.append(link.get('href'))

	## Get all the play by play links from the box score links
	pbp = []
	boxes = [f'https://stats.ncaa.org/{s}' for s in links]

	def scrapeLinks(url):
		soup = BeautifulSoup(requests.get(url, headers = {"User-Agent": "Mozilla/5.0"}).content, 'lxml')
		link = soup.find('a', attrs={'href': re.compile("/play_by_play")})
		if link is not None:
			return link.get('href')
		else:
			return ''

	for box in boxes:
		pbp.append(scrapeLinks(box))

	## For each game, get all of the plays with intended batter team
	games = [f'https://stats.ncaa.org/{s}' for s in pbp if pbp != '']
	def gameScraper(game):

		allPlays = []
		plays = []
		soup = BeautifulSoup(requests.get(game, headers = {"User-Agent": "Mozilla/5.0"}).content, 'lxml')
		## filter out missing games
		if len(soup) > 1:
		## Get the date from the top of the play by play page
			try:
				date = soup.find(text='Game Date:').parent.parent.findNext('td', attrs={'class': None}).text.strip()
				date = date[6:10] + date[0:2] + date[3:5]
			except:
				date = None

			## Plays are stored in a 3-column table. This is how we identify which column we want
			index = 10
			for i, td in enumerate(soup.find('table', {'class': 'mytable', 'width': '1000px'}).find('tr', {'class': 'grey_heading'}).findAll('td')):
				if td.text not in teamNameList and td.text != 'Score':
					oppTeamName = td.text
					if oppTeamName in teamNameDict:
						oppTeamName = teamNameDict[oppTeamName]
				if td.text in teamNameList or bool([x for x in teamNameList if td.text in x.split()]):
					index = i

			if index < 10:
				oppTeam = team_dim.query.filter_by(NAME=oppTeamName).first()
				if oppTeam != None:
					ptk = oppTeam.TEAM_KEY
				else:
					ptk = None


				for table in soup.findAll('table', {'class': 'mytable', 'width': '1000px'}):
					for play in table.findAll('tr', {'class': None}):
						## Select the correct column
						string = play.select_one(f"tr td:nth-of-type({index+1})").text.replace("\n", '')
						if len(string) > 5 and len([pl for pl in unwanted if(pl in string)]) == 0:
							plays.append(string)
				for play in plays:
					play = play.replace('3a', ';').replace('unassisted', '')
					play_details = {}
					play_details['date'] = date
					play_details['btk'] = team
					play_details['ptk'] = ptk
					play_details['description'] = play
					## get the first 3 words -- contains the batters names
					start = ' '.join(play.split(' ')[0:3])
					start = re.compile('|'.join(map(re.escape, outcomes2))).sub('', start)
					start = start.split(';')[0]


					## store all potential batters in the subject list
					## if multiple perfect matches, take the longer one to avoid subsets i.e Brown vs Browning or A. Smith vs B. Smith
					subject = []
					matchLen = 0
					for p in roster:
						for pl in players[p.PLAYER_KEY]:
							if pl in start and len(pl) >= matchLen and p.PLAYER_KEY not in subject:
								if len(pl) > matchLen:
									subject = []
								matchLen = len(pl)
								subject.append(p.PLAYER_KEY)


					# If there are none, check if there's a slight misspell in the first word
					if len(subject) == 0:
						for p in roster:
							if bool([pl for pl in players[p.PLAYER_KEY] if(dist(pl,start.split(' ')[0]))]):
								subject.append(p.PLAYER_KEY)

					# Or check if there's a slight misspell in the first 2 words
					if len(subject) == 0:
						for p in roster:
							if bool([pl for pl in players[p.PLAYER_KEY] if(dist(pl,' '.join(start.split(' ')[0:2])))]):
								subject.append(p.PLAYER_KEY)

					# Or check if there's a slight misspell in the first 3 words
					if len(subject) == 0:
						for p in roster:
							if bool([pl for pl in players[p.PLAYER_KEY] if(dist(pl,' '.join(start.split(' ')[0:3])))]):
								subject.append(p.PLAYER_KEY)


					# if there are still 2 check which one has the closest spelling
					if len(subject) > 1:
						cor = []
						distance = 0
						for s in subject:
							for p in players[s]:
								distNew = calcDist(p, ' '.join(start.split(' ')[0:3]))
								if distNew >= distance:
									if distNew > distance:
										cor = []
									distance = distNew
									act = p
									if s not in cor:
										cor.append(s)
						subject = cor


					# if there are still 2, check partial distances
					if len(subject) > 1:
						cor = []
						distance = 0
						for s in subject:
							for p in players[s]:
								distNew = partialDist(p, ' '.join(start.split(' ')[0:3]))
								if distNew >= distance:
									if distNew > distance:
										cor = []
									distance = distNew
									if s not in cor:
										cor.append(s)
						subject = cor

					## if still more than 1, check if one is a pitcher
					if len(subject) > 1:
						ros = [r.PLAYER_KEY for r in roster if r.PLAYER_KEY in subject and r.POSITION.upper() not in ('P', 'RP', 'SP', 'RHP', 'LHP', 'LHRP', 'RHRP', 'LHSP', 'RHSP')]
						if len(ros) == 1:
							subject = []
							subject.append(ros[0])

					subject = subject[0] if len(subject) > 0 else None


					play_details['batter'] = subject

					loc = [l for l in locMult if(l in play)]
					if len(loc) == 0:
						loc = [l for l in locations if(l in play)]

					if 'double play' in play:
						dpLoc = [str(play.split('play')[1]).split(' ')]
						for l in dpLoc:
							if l in locations:
								loc = l
								break

					indLoc = 1000
					if len(loc) > 1:
						for l in loc:
							indexLoc = play.find(l)

							if indexLoc < indLoc:
								indLoc = indexLoc
								loc = [l]
					loc = loc[0].replace('.','').replace(',','').replace(';','').strip() if len(loc) > 0 else None
					loc = None if loc == 'ss' and 'passed ball' in play else loc
					play_details['location'] = loc

					out = [t for t in outcomes if(t in play)]


					indOut = 1000
					if len(out) > 1:
						for t in out:
							indexOut = play.find(t)

							if indexOut < indOut:
								indOut = indexOut
								out = [t]
					out = out[0].strip() if len(out) > 0 else None


					if out is not None:
						if out == 'error':
							if loc in ['lf', 'rf', 'cf', 'left', 'right', 'center']:
								play_details['outcome'] = 'FB'
							else:
								play_details['outcome'] = 'GB'
						else:
							play_details['outcome'] = outDict[out]
					else:
						play_details['outcome'] = None
					allPlays.append(play_details)
			return allPlays

	allPlays = []
	for game in games:
		try:
			thesePlays = gameScraper(game)
			if len(thesePlays) > 0:
				allPlays.append(thesePlays)
		except:
			continue
	allPlays = list(itertools.chain.from_iterable(allPlays))

	url=f'https://stats.ncaa.org/team/{team}/stats/{yearCodes[str(year)]}'
	soup = BeautifulSoup(requests.get(url, headers = {"User-Agent": "Mozilla/5.0"}).content, 'html.parser')
	table = soup.find('tbody')
	head = soup.find('thead').findAll('th')
	index = 6
	for i, d in enumerate(head):
		if d.text == 'BA':
			index = i
			break

	ibb = 0 if int(year) < 2019 else 1
	for i, d in enumerate(head):
		if d.text == 'IBB':
			ibb = 1
			break

	rosterToAdd = []
	if table is not None:
		for row in table.findAll('tr'):
			cells = []
			for cell in row.findAll('td'):
				text = cell.text.replace("\n", '')
				text = cell.text.replace('nbsp&', '')
				cells.append(text)
				# name
			rosterToAdd.append(hitter_stats(cells[1].replace('â€™',"'").replace("\n", ''),
			# position
			cells[3].replace("\n", ''),
			# jersey
			cells[0].replace("\n", ''),
			# class
			cells[2].replace("\n", ''),
			year,
			# games
			cells[4].replace("\n", ''),
			# games started
			cells[5].replace("\n", ''),
			# AB
			cells[11].replace("\n", ''),
			# BA
			cells[index].replace("\n", ''),
			# OBP
			cells[8].replace("\n", ''),
			#SLG
			cells[9].replace("\n", ''),
			#K
			cells[22].replace("\n", ''),
			#BB
			cells[18].replace("\n", ''),
			#SB
			cells[26].replace("\n", ''),
			#CS
			cells[24].replace('\n', ''),
			# IBB
			0 if ibb == 0 else cells[27].replace("\n", ''),
			# HBP
			cells[19].replace("\n", ''),
			#SF
			cells[20].replace("\n", ''),
			#SH
			cells[21].replace("\n", ''),
			#R
			cells[10].replace("\n", ''),
			#RBI
			cells[17].replace("\n", ''),

			team))

	play_by_play.query.filter_by(YEAR=int(year)).filter_by(BATTER_TEAM_KEY=team).delete()
	for play in allPlays:
		try:
			pbp = play_by_play(play['date'], play['batter'], play['btk'], play['ptk'], play['outcome'], play['location'], year, play['description'])
			db.session.add(pbp)
		except:
			continue
	db.session.commit()
	lastName = ''
	lastNum = ''
	for player in rosterToAdd:
		## handle duplicate roster entries
		name = player.FULL_NAME
		num = player.NUMBER
		try:
			if name != lastName and num != lastNum:
				db.session.merge(player)
		except:
			continue
		lastName = player.FULL_NAME
		lastNum = player.NUMBER
	gc.collect()
	return jsonify(allPlays)


	gc.collect()
	return 'no'


@app.route('/data', methods = ['POST', 'GET'])
def data():
	query = f"""
	SELECT t.NAME, t.TEAM_KEY, t.ACTIVE_RECORD,
	CAST(IFNULL(ROS_0, 0) as signed) ROS_0,
	CAST(IFNULL(ROS_1, 0) as signed) ROS_1,
	CAST(IFNULL(ROS_2, 0) as signed) ROS_2,
	CAST(IFNULL(PBP_0, 0) as signed) PBP_0,
	CAST(IFNULL(PBP_1, 0) as signed) PBP_1,
	CAST(IFNULL(PBP_2, 0) as signed) PBP_2
	FROM TEAM_DIM t
	LEFT JOIN (
	SELECT TEAM_KEY,
	SUM(CASE WHEN YEAR = {years[0]} THEN 1 ELSE 0 END) as ROS_0,
	SUM(CASE WHEN YEAR = {years[1]} THEN 1 ELSE 0 END) as ROS_1,
	SUM(CASE WHEN YEAR = {years[2]} THEN 1 ELSE 0 END) as ROS_2
	 FROM PLAYER_DIM
	 GROUP BY TEAM_KEY
	 ) a on a.TEAM_KEY = t.TEAM_KEY
	 LEFT JOIN
	(
	SELECT
	BATTER_TEAM_KEY,
	MAX(CASE WHEN YEAR = {years[0]} THEN DATE_KEY ELSE 0 END) as PBP_0,
	MAX(CASE WHEN YEAR = {years[1]} THEN DATE_KEY ELSE 0 END) as PBP_1,
	MAX(CASE WHEN YEAR = {years[2]} THEN DATE_KEY ELSE 0 END) as PBP_2
	 FROM PLAY_BY_PLAY
	 GROUP BY BATTER_TEAM_KEY
	) b on b.BATTER_TEAM_KEY = t.TEAM_KEY
	WHERE t.ACTIVE_RECORD = 1 {string}
	ORDER BY NAME;
	"""
	status = list(db.engine.execute(query))

	return render_template('data.html', status=status, data = jsonDump(status), years=years)


@app.route('/sprays', methods = ['POST', 'GET'])
def sprays():
	team = request.values.get('team', '')
	if team != '':
		team = int(team)
	data = db.engine.execute(f"""SELECT p.TEAM_KEY, NAME, COUNT(*) FROM PLAYER_DIM p
	JOIN TEAM_DIM t on t.TEAM_KEY = p.TEAM_KEY
	WHERE p.ACTIVE_RECORD = 1 and t.ACTIVE_RECORD = 1
	GROUP BY p.TEAM_KEY;""")
	teams = []
	for d in data:
		teams.append({'NAME': d.NAME, 'TEAM_KEY': d.TEAM_KEY})
	stats = []
	plays = []
	rosters = []
	row = team_dim.query.filter_by(TEAM_KEY=team).first()
	if team == '' or row is None:
		return render_template('sprays.html', team = team, stats = jsonDump(stats), plays = jsonDump(plays), rosters = jsonDump(rosters), data = jsonDump(teams), years = years)

	num = row.VISITS
	db.engine.execute(f"""UPDATE TEAM_DIM SET VISITS = {num+1} WHERE TEAM_KEY = {team}""")

	plays = list(db.engine.execute(f"""SELECT p.*, FULL_NAME FROM PLAY_BY_PLAY p
	 JOIN PLAYER_DIM d on d.PLAYER_KEY = p.BATTER_PLAYER_KEY
	 WHERE d.ACTIVE_RECORD = 1 AND BATTER_TEAM_KEY = {team} and p.ACTIVE_RECORD = 1 """))
	rosters = list(db.engine.execute(f"""SELECT * FROM PLAYER_DIM WHERE TEAM_KEY = {team} AND ACTIVE_RECORD = 1"""))
	stats = list(db.engine.execute(f"""SELECT * FROM HITTER_STATS WHERE TEAM_KEY = {team} AND ACTIVE_RECORD = 1"""))
	return render_template('sprays.html', team = team, stats = jsonDump(stats), plays = jsonDump(plays), rosters = jsonDump(rosters), data = json.dumps(teams), years = years)

@app.route('/printSprays', methods = ['POST', 'GET'])
def printSprays():
	key = request.values.get('keys', '')
	team = request.values.get('team', '')
	if team != '':
		team = int(team)
	year = request.values.get('year', '')
	if year != '':
		year = int(year)
	c = request.values.get('c','')
	if c == 'c':
		name = player_dim.query.filter_by(PLAYER_KEY=key).first().FULL_NAME
		plays = list(db.engine.execute(f"""
		SELECT d.FULL_NAME, d.NUMBER, p.* FROM PLAY_BY_PLAY p
		JOIN PLAYER_DIM d on d.PLAYER_KEY = p.BATTER_PLAYER_KEY
		WHERE FULL_NAME = '{name}' and d.TEAM_KEY = {team} and p.ACTIVE_RECORD = 1
		"""))
		stats = list(db.engine.execute(f"""
		SELECT * FROM HITTER_STATS
		WHERE ACTIVE_RECORD = 1 and FULL_NAME = '{name}' and TEAM_KEY = {team}"""))
		return render_template('printSpraysC.html', name = name, stats = jsonDump(stats), plays = jsonDump(plays))

	if key != '':
		keys = int(key)
		keyList = [keys]

	if key == '':
		keys = list(db.engine.execute(f"""SELECT * FROM PLAYER_DIM
		WHERE TEAM_KEY = {team} and YEAR = {year} and ACTIVE_RECORD = 1"""))
		keyList = [str(x.PLAYER_KEY) for x in keys]
		keys = ', '.join(keyList)

	plays = list(db.engine.execute(f"""
	SELECT d.FULL_NAME, d.NUMBER, p.* FROM PLAY_BY_PLAY p
	JOIN PLAYER_DIM d on d.PLAYER_KEY = p.BATTER_PLAYER_KEY
	WHERE BATTER_PLAYER_KEY in ({keys}) and p.ACTIVE_RECORD = 1
	"""))

	stats = list(db.engine.execute(f"""
	SELECT p.PLAYER_KEY, h.* FROM HITTER_STATS h
	JOIN PLAYER_DIM p on p.FULL_NAME = h.FULL_NAME
	and h.TEAM_KEY = p.TEAM_KEY and h.NUMBER = p.NUMBER
	and h.POSITION = p.POSITION and h.CLASS = p.CLASS and h.YEAR = p.YEAR
	WHERE p.PLAYER_KEY in ({keys})
	"""))

	return render_template('printSprays.html', keys = keyList, plays = jsonDump(plays),
	stats = jsonDump(stats))


@app.route('/about')
def about():
	return render_template('about.html')

@app.route('/faq')
def faq():
	return render_template('faq.html')



@app.route('/editPlays')
def editPlays():
	# currently unused
	return '1'

	team_key = int(equest.values.get('team', '755'))
	year = int(request.values.get('year', years[0]))

	playsORG = list(db.engine.execute(f"""SELECT p.FULL_NAME NAME, t.NAME TEAM_NAME, pbp.* FROM PLAY_BY_PLAY pbp
 	LEFT JOIN PLAYER_DIM p on p.PLAYER_KEY = pbp.BATTER_PLAYER_KEY
 	LEFT JOIN TEAM_DIM t on t.TEAM_KEY = pbp.BATTER_TEAM_KEY
	WHERE t.TEAM_KEY = {team_key} and pbp.YEAR = {year}
 	ORDER BY p.PLAYER_KEY
 	 """))
	name = ''
	if len(playsORG) > 0:
		name = str(playsORG[0].TEAM_NAME)

	return render_template('editPlays.html', org = name, key = team_key, year = year,playsJS = json.dumps([dict(r) for r in playsORG]))


@app.route('/PBPWrite')
def PBPWrite():
	id = request.values.get('id','')
	col = request.values.get('col', '')
	val = request.values.get('val', '')
	if id != '':
		play = play_by_play.query.filter_by(PLAY_ID=id).first()
		if col == 'ar':
			play.ACTIVE_RECORD = play.ACTIVE_RECORD*-1 + 1
			db.session.commit()
		if col == 'loc':
			play.LOCATION = val
			db.session.commit()
		return 'yes'
	else:
		return 'no'




@app.route('/getData/<key>/<year>/<type>/<csv>', methods = ['POST', 'GET'])
def getData(key, year, type, csv):
	# currently unused
	return '1'
	if key != '' and year != '' and type != '' and len(key) < 10 and len(year) < 5 and len(type) < 10:
		if type == 'pbpT':
			tab = 'PLAY_BY_PLAY'
			keyCol = 'BATTER_TEAM_KEY'
			order = 'DATE_KEY'
		elif type == 'pbpP':
			tab = 'PLAY_BY_PLAY'
			keyCol = 'BATTER_PLAYER_KEY'
			order = 'DATE_KEY'
		elif type == 'ros':
			tab = 'PLAYER_DIM'
			keyCol = 'TEAM_KEY'
			order = 'FULL_NAME'
		query = f"""SELECT * FROM {tab} WHERE {keyCol} = {key} and YEAR = {year} and ACTIVE_RECORD = 1 ORDER BY {order}"""
		if ';' not in query:
			data = list(db.engine.execute(query))
		else:
			data = []
	else:
		data = []

	if csv == 'y':
		if len(data) > 0:
			df = pd.DataFrame(data, columns = dict(data[0]).keys())
			csv = df.to_csv(index=False)
			output = make_response(csv)
			output.headers["Content-Disposition"] = "attachment; filename=export.csv"
			output.headers["Content-type"] = "text/csv"
			return output
	return jsonDump(data)


@app.route('/getStats/<name>/<num>/<pos>/<fresh>/<year>/<team>', methods = ['POST', 'GET'])
def getStats(name, num, pos, fresh, year, team):
	## currently unused
	return '1'
	string = f"""SELECT * FROM HITTER_STATS WHERE FULL_NAME = '{name}' and NUMBER = '{num}' and POSITION = '{pos}' and YEAR = '{year}' and CLASS = '{fresh}' and TEAM_KEY = '{team}'"""
	if ';' not in string:
		data = list(db.engine.execute(string))
	else:
		data = []
	return jsonDump(data)
