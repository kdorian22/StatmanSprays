from flask import *
from flask_jsglue import JSGlue
from flask_sqlalchemy import SQLAlchemy
import requests
import pandas as pd
from bs4 import BeautifulSoup
import numpy as np
import re
import os, sys
import subprocess
from datetime import datetime
from app import app, db
from app.models import *


jsglue = JSGlue(app)

yearCodes = {
		 '2020': '15204',
		 '2019':'14781',
		 '2018':'12973',
		 '2017':'12560',
		 '2016':'12360'}

statCodes = {
		 'hit': '14760',
		 'pitch':'14761',
		 'field':'14762'}

locations = ['1b', '2b', '3b', 'ss', ' p ', ' p.', ' p,', ' c ', ' c.', ' c,', 'catcher', 'pitcher',
' lf', ' rf', ' cf', 'shortstop', 'center',
'lcf', 'rcf',
'1b line', '3b line', 'left', 'right',
]

locMult = ['through the left side', 'through the right side', 'up the middle', 'left field line',
'right field line', 'left center', 'right center', 'third base', 'first bsae', 'second base',
'rf line', 'lf line']

outcomes = ['grounded','muffed','error','line','lined','flied','force','pop','single','double','triple','home','choice','foul','bunt']

outMult = ['out at']

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
 'pop': 'FB',
 'foul': 'FB'
 }

@app.template_filter()
def date(text):
	text = str(text)
	if len(text) == 8:
		text = text[4:6] + '-' + text[6:8] + '-' + text[0:4]
	return text

@app.route('/')
def index():
	query = """SELECT * FROM TEAM_DIM"""
	data = list(db.engine.execute(query))
	return render_template('index.html', data = json.dumps([dict(r) for r in data]))


@app.route('/scrapeTeams', methods = ['GET'])
def scrapeTeams():
	team_dim.query.delete()
	db.session.commit()
	url='https://stats.ncaa.org/game_upload/team_codes'
	page = requests.get(url)
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
			ele = team_dim(str(team[1]), int(team[0]), 1)
			db.session.add(ele)
			# db.engine.execute(f"""
			#  INSERT INTO TEAM_DIM (NAME, TEAM_KEY)
			# VALUES ("{team[1]}", {int(team[0])})""")
	except:
		return {'result': 'upload failed'}
	db.session.commit()
	return {'result': 'upload successful'}


@app.route('/scrapeRoster', methods = ['GET'])
def scrapeRoster():
	db.session.commit()
	year = request.values.get('year','2020')
	team = request.values.get('team','')
	r = request.values.get('r', '')

	exists = player_dim.query.filter_by(YEAR=str(year)).filter_by(TEAM_KEY=team).all()
	if len(exists) > 0 and r == '':
		return 'Already Scraped'
	else:
		player_dim.query.filter_by(YEAR=str(year)).filter_by(TEAM_KEY=team).delete()
		db.session.commit()
		i = 0
		url=f'https://stats.ncaa.org/team/{team}/roster/{yearCodes[year]}'
		soup = BeautifulSoup(requests.get(url).content, 'lxml')
		table = soup.find('tbody')
		if table is not None:
			for row in table.findAll('tr'):
				cells = []
				for cell in row.findAll('td'):
					text = cell.text.replace("\n", '')
					text = cell.text.replace('nbsp&', '')
					cells.append(text)
				player = player_dim(cells[0], cells[1], cells[2], cells[3], year, team)
				db.session.add(player)
			i = i+1
			if i % 10 == 0:
				db.session.commit()
		else:
			db.engine.execute(f"""
			UPDATE TEAM_DIM SET ACTIVE_RECORD = 0 WHERE TEAM_KEY = {team}
			""")
			db.session.commit()
			return 'no'


	change = player_dim.query.filter_by(NUMBER=4).filter_by(TEAM_KEY=16).filter_by(CLASS='So').first()
	change.ACTIVE_RECORD = 0
	db.session.commit()
	players = list(db.engine.execute(f"SELECT * FROM PLAYER_DIM WHERE YEAR = '{year}' and TEAM_KEY = {team}"))
	return json.dumps([dict(e) for e in players])


@app.route('/scrapePlays', methods = ['POST', 'GET'])
def scrapePlays():
	db.session.commit()
	team = request.values.get('team', '755')
	year = request.values.get('year', '2020')
	## Get team name

	play_by_play.query.filter_by(YEAR=int(year)).filter_by(BATTER_TEAM_KEY=team).delete()


	teamName = team_dim.query.filter_by(TEAM_KEY=team).first().NAME

	## Get team roster
	roster = player_dim.query.filter_by(TEAM_KEY=team).filter_by(YEAR=year).all()
	if len(roster) == 0:
		return 'no roster'
	players = {}
	playersNotLast = {}

	## For each guy on the roster, list the different ways his name can be stored
	for r in roster:
		names = []
		namesNotLast = []
		full = r.FULL_NAME.split(', ')
		last = full[0].split(' ')
		names.append(full[1] + ' ' + full[0])
		names.append(full[1][0] + '. ' + full[0])
		names.append(full[1][0] + '.' + full[0])
		names.append(full[1][0] + full[0])
		names.append(full[0] + ', ' + full[1][0]+'.')
		names.append(full[0] + ', ' + full[1][0])
		names.append(full[0] + ',' + full[1][0]+'.')
		names.append(full[0] + ',' + full[1][0])
		names.append(full[1][0:2] + '. ' + full[0])
		names.append(full[1][0:3] + '. ' + full[0])
		names.append(full[0])
		names.append(r.FULL_NAME)
		namesNotLast.append(full[1] + ' ' + full[0])
		namesNotLast.append(full[1][0] + '. ' + full[0])
		namesNotLast.append(full[1][0] + '.' + full[0])
		namesNotLast.append(full[1][0] + full[0])
		namesNotLast.append(full[0] + ', ' + full[1][0]+'.')
		namesNotLast.append(full[0] + ', ' + full[1][0])
		namesNotLast.append(full[0] + ',' + full[1][0]+'.')
		namesNotLast.append(full[0] + ',' + full[1][0])
		namesNotLast.append(full[1][0:2] + '. ' + full[0])
		namesNotLast.append(full[1][0:3] + '. ' + full[0])
		namesNotLast.append(r.FULL_NAME)
		if "'" in r.FULL_NAME:
			names.append(r.FULL_NAME.replace("'",'').replace("'",''))
			names.append(full[0].replace("'",'').replace("'",''))
			namesNotLast.append(r.FULL_NAME.replace("'",'').replace("'",''))
		if len(last) == 2:
			names.append(last[0][0] + '. ' + last[1])
			namesNotLast.append(last[0][0] + '. ' + last[1])
		names = names + [x.upper() for x in names]
		namesNotLast = namesNotLast + [x.upper() for x in namesNotLast]
		players[r.PLAYER_KEY] = names
		playersNotLast[r.PLAYER_KEY] = namesNotLast

	unwanted = ['picked off', 'caught stealing', 'struck', 'walked', 'stole', 'for']
	## start on the team-year roster page
	start = f'https://stats.ncaa.org/team/{team}/roster/{yearCodes[year]}'
	soup = BeautifulSoup(requests.get(start).content, 'lxml')

	## Get possible links to list of games
	direct = []

	for link in soup.findAll('a', attrs={'href': re.compile("^/teams")}):
		direct.append(link.get('href'))
	if len(direct) == 0:
		db.engine.execute(f"""
		UPDATE TEAM_DIM SET ACTIVE_RECORD = 0 WHERE TEAM_KEY = {team}
		""")
		db.session.commit()
		return 'no'

	## Get the link to the list of games. There are two similar links; we need the third one down
	url = "https://stats.ncaa.org" + direct[2]
	soup = BeautifulSoup(requests.get(url).content, 'lxml')

	## Get all the box score links. Different attribute depending on year
	links = []
	target = 'BOX_SCORE_WINDOW' if int(year) >= 2019 else 'TEAM_WIN'
	for link in soup.findAll('a', attrs={'target': target}):
		links.append(link.get('href'))

	## Get all the play by play links from the box score links
	pbp = []
	boxes = [f'https://stats.ncaa.org/{s}' for s in links]
	for url in boxes[0:]:
		soup = BeautifulSoup(requests.get(url).content, 'lxml')
		link = soup.find('a', attrs={'href': re.compile("/play_by_play")})
		if link is not None:
			pbp.append(link.get('href'))

	## For each game, get all of the plays with intended batter team
	games = [f'https://stats.ncaa.org/{s}' for s in pbp]
	allPlays = []
	for game in games:
		plays = []

		soup = BeautifulSoup(requests.get(game).content, 'lxml')
		## Get the date from the top of the play by play page
		date = soup.find(text='Game Date:').parent.parent.findNext('td', attrs={'class': None}).text.strip()
		try:
			date = date[6:10] + date[0:2] + date[3:5]
		except:
			date = None

		## Plays are stored in a 3-column table. This is how we identify which column we want
		index = 10
		for i, td in enumerate(soup.find('table', {'class': 'mytable', 'width': '1000px'}).find('tr', {'class': 'grey_heading'}).findAll('td')):
			if td.text != teamName and td.text != 'Score':
				oppTeamName = td.text
			if td.text == teamName or (td.text in teamName.split()):
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
				start = ' '.join(play.split(' ')[0:4])


				## store all potential batters in the subject list
				subject = []

				for p in roster:
					if bool([pl for pl in players[p.PLAYER_KEY] if(pl in start)]):
						subject.append(p.PLAYER_KEY)


				## if more than 1 potential subject, check again, but don't look for last names
				if len(subject) > 1:
					subject = []
					for p in roster:
						if bool([pl for pl in playersNotLast[p.PLAYER_KEY] if(pl in start)]):
							subject.append(p.PLAYER_KEY)

				subject = subject[0] if len(subject) > 0 else None
				play_details['batter'] = subject

				loc = [l for l in locMult if(l in play)]
				if len(loc) == 0:
					loc = [l for l in locations if(l in play)]

				if 'double play' in play:
					loc = [str(play.split('play ')[1]).split(' ')[0]]

				indLoc = 1000
				if len(loc) > 1:
					for l in loc:
						indexLoc = play.find(l)

						if indexLoc < indLoc:
							indLoc = indexLoc
							loc = [l]
				loc = loc[0].replace('.','').replace(',','').strip() if len(loc) > 0 else None
				loc = None if loc == 'ss' and 'passed ball' in play else loc
				play_details['location'] = loc

				out = [t for t in outMult if(t in play)]
				if len(out) == 0:
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
				pbp = play_by_play(play_details['date'], play_details['batter'], play_details['btk'], play_details['ptk'], play_details['outcome'], play_details['location'], year, play_details['description'])
				db.session.add(pbp)
				db.session.commit()
				allPlays.append(play_details)

	return jsonify(allPlays)


@app.route('/getData/<key>/<year>/<type>', methods = ['POST', 'GET'])
def getData(key, year, type):
	print(key, year, type)
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

		data = list(db.engine.execute(
			f"""SELECT * FROM {tab} WHERE {keyCol} = {key} and YEAR = {year} ORDER BY {order}"""
		))
	else:
		data = []
	return json.dumps([dict(d) for d in data])



@app.route('/updateDB', methods = ['POST', 'GET'])
def updateDB():
	status = list(db.engine.execute(f"""
		With a as (
		SELECT
		TEAM_KEY,
		SUM(CASE WHEN YEAR = 2020 THEN 1 ELSE 0 END) as ROS_20,
		SUM(CASE WHEN YEAR = 2019 THEN 1 ELSE 0 END) as ROS_19,
		SUM(CASE WHEN YEAR = 2018 THEN 1 ELSE 0 END) as ROS_18
		 FROM PLAYER_DIM
		 GROUP BY TEAM_KEY
		 )
		, b as (
		SELECT
		BATTER_TEAM_KEY,
		MAX(CASE WHEN YEAR = 2020 THEN DATE_KEY ELSE 0 END) as PBP_20,
		MAX(CASE WHEN YEAR = 2019 THEN DATE_KEY ELSE 0 END) as PBP_19,
		MAX(CASE WHEN YEAR = 2018 THEN DATE_KEY ELSE 0 END) as PBP_18
		 FROM PLAY_BY_PLAY
		 GROUP BY BATTER_TEAM_KEY
		)
		SELECT t.NAME, t.TEAM_KEY, t.ACTIVE_RECORD,
		CASE WHEN ROS_20 IS NULL THEN 0 ELSE ROS_20 END ROS_20,
		CASE WHEN ROS_19 IS NULL THEN 0 ELSE ROS_19 END ROS_19,
		CASE WHEN ROS_18 IS NULL THEN 0 ELSE ROS_18 END ROS_18,
		CASE WHEN PBP_20 IS NULL THEN 0 ELSE PBP_20 END PBP_20,
		CASE WHEN PBP_19 IS NULL THEN 0 ELSE PBP_19 END PBP_19,
		CASE WHEN PBP_18 IS NULL THEN 0 ELSE PBP_18 END PBP_18
		FROM TEAM_DIM t
		LEFT JOIN a on a.TEAM_KEY = t.TEAM_KEY
		LEFT JOIN b on b.BATTER_TEAM_KEY = t.TEAM_KEY
		WHERE t.ACTIVE_RECORD = 1
		"""))
	return render_template('updateDB.html', status=status, data = json.dumps([dict(s) for s in status]))


@app.route('/sprays', methods = ['POST', 'GET'])
def sprays():
	teams = db.engine.execute(f"""
	with a as (SELECT BATTER_TEAM_KEY TEAM_KEY, COUNT(*), YEAR  FROM
	PLAY_BY_PLAY
	GROUP BY BATTER_TEAM_KEY, YEAR)
	SELECT a.*, NAME FROM a
	JOIN TEAM_DIM t on t.TEAM_KEY = a.TEAM_KEY
	ORDER BY NAME, a.YEAR
	""")
	return render_template('sprays.html', teams=teams, data = json.dumps([dict(s) for s in teams]))
