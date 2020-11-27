from flask import *
from flask_jsglue import JSGlue
from flask_sqlalchemy import SQLAlchemy
import requests
import pandas as pd
from bs4 import BeautifulSoup
import numpy as np
import re
from datetime import datetime
from statman import app, db
from statman.models import *
from fuzzywuzzy import fuzz
import Levenshtein as lev
import gc


jsglue = JSGlue(app)
app.config['PDF_FOLDER'] = 'static/pdf/'

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

locations = ['1b', '2b', '3b', 'ss', ' p ', ' p.', ' p,',' p;', ' c ', ' c.', ' c,', 'catcher', 'pitcher',
' lf', ' rf', ' cf', 'shortstop', 'center',
'lcf', 'rcf',
'1b line', '3b line', 'left', 'right',
]

locMult = ['through the left side', 'through the right side', 'up the middle', 'left field line',
'right field line', 'left center', 'right center', 'third base', 'first base', 'second base',
'rf line', 'lf line']

outcomes = ['grounded','muffed','error','line','lined','flied','fly','force','pop','single','double','triple','home','choice','foul','bunt', 'out at']

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

@app.route('/')
def index():
	return render_template('index.html')


@app.route('/scrapeTeams', methods = ['GET'])
def scrapeTeams():
	team_dim.query.delete()
	db.session.commit()
	url='https://stats.ncaa.org/game_upload/team_codes'
	page = requests.get(url, headers = {"User-Agent":"Mozilla/5.0"})
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
	try:
		db.session.commit()
		allow = list(db.engine.execute(f"""
		SELECT * from ALLOW_SCRAPE
		"""))[0].ALLOW
		time_last = list(db.engine.execute(f"""
		SELECT * from ALLOW_SCRAPE
		"""))[0].TIME

		now = datetime.now()
		time_now = int(str(now.year) + str(now.month) + str(now.day) + str(now.hour) + str(now.minute))

		if allow == 1 or (time_now - time_last > 10):
			db.engine.execute("UPDATE ALLOW_SCRAPE SET ALLOW = 0")
			db.engine.execute(f"UPDATE ALLOW_SCRAPE SET TIME = {time_now}")
			db.session.commit()
			exists = player_dim.query.filter_by(YEAR=str(year)).filter_by(TEAM_KEY=team).all()
			if len(exists) > 0 and r == '':
				db.session.commit()
				db.engine.execute(f"""
				UPDATE TEAM_DIM SET ACTIVE_RECORD = 0 WHERE TEAM_KEY = {team}
				""")
				db.session.commit()
				db.engine.execute("UPDATE ALLOW_SCRAPE SET ALLOW = 1")
				db.session.commit()
				return 'Already Scraped'
			else:
				player_dim.query.filter_by(YEAR=str(year)).filter_by(TEAM_KEY=team).delete()
				db.session.commit()
				i = 0
				url=f'https://stats.ncaa.org/team/{team}/roster/{yearCodes[year]}'
				soup = BeautifulSoup(requests.get(url, headers = {"User-Agent":"Mozilla/5.0"}).content, 'lxml')
				table = soup.find('tbody')
				if table is not None:
					for row in table.findAll('tr'):
						cells = []
						for cell in row.findAll('td'):
							text = cell.text.replace("\n", '')
							text = cell.text.replace('nbsp&', '')
							cells.append(text)
						player = player_dim(cells[0].replace('â€™',"'"), cells[1], cells[2], cells[3], year, team)
						db.session.add(player)
					i = i+1
					if i % 10 == 0:
						db.session.commit()
				else:
					db.session.commit()
					# db.engine.execute(f"""
					# UPDATE TEAM_DIM SET ACTIVE_RECORD = 0 WHERE TEAM_KEY = {team}
					# """)
					db.session.commit()
					db.engine.execute("UPDATE ALLOW_SCRAPE SET ALLOW = 1")
					db.session.commit()
					return 'no'


			change = player_dim.query.filter_by(NUMBER=4).filter_by(TEAM_KEY=16).filter_by(CLASS='So').first()
			if change is not None:
				change.ACTIVE_RECORD = 0
			db.session.commit()
			players = list(db.engine.execute(f"SELECT * FROM PLAYER_DIM WHERE YEAR = '{year}' and TEAM_KEY = {team}"))
			db.session.commit()
			db.engine.execute("UPDATE ALLOW_SCRAPE SET ALLOW = 1")
			db.session.commit()
			return json.dumps([dict(e) for e in players])
		else:
			return 'use'
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
		dist = max([fuzz.ratio(a.lower(),b.lower())/100, fuzz.partial_ratio(a.lower(),b.lower())])
	else:
		dist = 0
	return dist



@app.route('/scrapePlays', methods = ['POST', 'GET'])
def scrapePlays():
	db.session.commit()
	allow = list(db.engine.execute(f"""
	SELECT * from ALLOW_SCRAPE
	"""))[0].ALLOW
	time_last = list(db.engine.execute(f"""
	SELECT * from ALLOW_SCRAPE
	"""))[0].TIME

	now = datetime.now()
	time_now = int(str(now.year) + str(now.month) + str(now.day) + str(now.hour) + str(now.minute))
	# try:
	if allow == 1 or (time_now - time_last >= 10):
		db.engine.execute("UPDATE ALLOW_SCRAPE SET ALLOW = 0")
		db.engine.execute(f"UPDATE ALLOW_SCRAPE SET TIME = {time_now}")
		db.session.commit()
		team = request.values.get('team', '755')
		year = request.values.get('year', '2020')
		## Get team name

		play_by_play.query.filter_by(YEAR=int(year)).filter_by(BATTER_TEAM_KEY=team).delete()


		teamName = team_dim.query.filter_by(TEAM_KEY=team).first().NAME

		## Get team roster
		roster = player_dim.query.filter_by(TEAM_KEY=team).filter_by(YEAR=year).all()
		if len(roster) == 0:
			db.session.commit()
			db.engine.execute("UPDATE ALLOW_SCRAPE SET ALLOW = 1")
			db.session.commit()
			return 'no roster'
		players = {}
		playersNotLast = {}

		## For each guy on the roster, list the different ways his name can be stored
		for r in roster:
			names = []
			full = r.FULL_NAME.split(', ')
			fullNS = full
			full = [f.replace(' ','') for f in full]
			last = fullNS[0].split(' ')
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
			players[r.PLAYER_KEY] = names
			playersNotLast[r.PLAYER_KEY] = namesNotLast
		unwanted = ['picked off', 'caught stealing', 'struck', 'walked', 'stole', 'for']
		## start on the team-year roster page
		start = f'https://stats.ncaa.org/team/{team}/roster/{yearCodes[year]}'
		soup = BeautifulSoup(requests.get(start, headers = {"User-Agent":"Mozilla/5.0"}).content, 'lxml')

		## Get possible links to list of games
		direct = []

		for link in soup.findAll('a', attrs={'href': re.compile("^/teams")}):
			direct.append(link.get('href'))
		if len(direct) == 0:
			db.session.commit()
			db.engine.execute(f"""
			UPDATE TEAM_DIM SET ACTIVE_RECORD = 0 WHERE TEAM_KEY = {team}
			""")
			db.session.commit()
			db.engine.execute("UPDATE ALLOW_SCRAPE SET ALLOW = 1")
			db.session.commit()
			return 'no'

		if len(direct) < 3:
			db.session.commit()
			db.engine.execute("UPDATE ALLOW_SCRAPE SET ALLOW = 1")
			db.session.commit()
			return 'no games'

		## Get the link to the list of games. There are two similar links; we need the third one down
		url = "https://stats.ncaa.org" + direct[2]
		soup = BeautifulSoup(requests.get(url, headers = {"User-Agent":"Mozilla/5.0"}).content, 'lxml')

		## Get all the box score links. Different attribute depending on year
		links = []
		target = 'BOX_SCORE_WINDOW' if int(year) >= 2019 else 'TEAM_WIN'
		for link in soup.findAll('a', attrs={'target': target}):
			links.append(link.get('href'))

		## Get all the play by play links from the box score links
		pbp = []
		boxes = [f'https://stats.ncaa.org/{s}' for s in links]
		for url in boxes[0:]:
			soup = BeautifulSoup(requests.get(url, headers = {"User-Agent":"Mozilla/5.0"}).content, 'lxml')
			link = soup.find('a', attrs={'href': re.compile("/play_by_play")})
			if link is not None:
				pbp.append(link.get('href'))

		## For each game, get all of the plays with intended batter team
		games = [f'https://stats.ncaa.org/{s}' for s in pbp]
		allPlays = []
		for game in games:
			try:
				plays = []

				soup = BeautifulSoup(requests.get(game, headers = {"User-Agent":"Mozilla/5.0"}).content, 'lxml')
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
							start = ' '.join(play.split(' ')[0:3])


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

							## if still more than 1, check if one is a pitcher
							if len(subject) > 1:
								ros = [r.PLAYER_KEY for r in roster if r.PLAYER_KEY in subject and r.POSITION.upper() not in ('P', 'RP', 'SP', 'RHP', 'LHP', 'LHRP', 'RHRP', 'LHSP', 'RHSP')]
								if len(ros) == 1:
									subject = []
									subject.append(ros[0])


							# ## if no potential subjects check to see if they just missed the last couple letters
							# if len(subject) == 0:
							# 	for p in roster:
							# 		if bool([pl for pl in players[p.PLAYER_KEY] if(pl[0:max([int(len(pl)*.66), 6])] in start)]):
							# 			subject.append(p.PLAYER_KEY)

							# Or check if theres a slight misspell in the first word
							if len(subject) == 0:
								for p in roster:
									if bool([pl for pl in players[p.PLAYER_KEY] if(dist(pl,start.split(' ')[0]))]):
										subject.append(p.PLAYER_KEY)

							# Or check if theres a slight misspell in the first 2 words
							if len(subject) == 0:
								for p in roster:
									if bool([pl for pl in players[p.PLAYER_KEY] if(dist(pl,' '.join(start.split(' ')[0:2])))]):
										subject.append(p.PLAYER_KEY)

							# Or check if theres a slight misspell in the first 3 words
							if len(subject) == 0:
								for p in roster:
									if bool([pl for pl in players[p.PLAYER_KEY] if(dist(pl,' '.join(start.split(' ')[0:3])))]):
										subject.append(p.PLAYER_KEY)

							# if there are still 2 check to see which one comes first and which one is closest if they start at the same spot
							if len(subject) > 1:
								cor = []
								distance = 0
								for s in subject:
									for p in players[s]:
										distNew = calcDist(p, ' '.join(start.split(' ')[0:3]))
										if distNew > distance:
											distance = distNew
											cor = []
											cor.append(s)
								subject = cor

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
							loc = loc[0].replace('.','').replace(',','').strip() if len(loc) > 0 else None
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

							if play_details['outcome'] == None and 'to' in start:
								play_details['batter'] = None


							pbp = play_by_play(play_details['date'], play_details['batter'], play_details['btk'], play_details['ptk'], play_details['outcome'], play_details['location'], year, play_details['description'])
							db.session.add(pbp)
							db.session.commit()
							allPlays.append(play_details)
			except:
				continue
		gc.collect()
		db.session.commit()
		db.engine.execute("UPDATE ALLOW_SCRAPE SET ALLOW = 1")
		db.session.commit()
		return jsonify(allPlays)
	else:
		return 'use'
	# except:
	# 	db.session.commit()
	# 	db.engine.execute(f"""
	# 	UPDATE TEAM_DIM SET ACTIVE_RECORD = 0 WHERE TEAM_KEY = {team}
	# 	""")
	# 	db.session.commit()
	# 	db.engine.execute("UPDATE ALLOW_SCRAPE SET ALLOW = 1")
	# 	db.session.commit()
	# 	return 'no'


@app.route('/getData/<key>/<year>/<type>', methods = ['POST', 'GET'])
def getData(key, year, type):
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
			f"""SELECT * FROM {tab} WHERE {keyCol} = {key} and YEAR = {year} and ACTIVE_RECORD = 1 ORDER BY {order}"""
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
		IFNULL(ROS_20, 0) ROS_20,
		IFNULL(ROS_19, 0) ROS_19,
		IFNULL(ROS_18, 0) ROS_18,
		IFNULL(PBP_20, 0) PBP_20,
		IFNULL(PBP_19, 0) PBP_19,
		IFNULL(PBP_18, 0) PBP_18
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
	return render_template('sprays.html', data = json.dumps([dict(s) for s in teams]))

@app.route('/printSprays', methods = ['POST', 'GET'])
def printSprays():
	keys = request.values.get('keys', '144')
	keyList = list(keys.split(','))
	plays = list(db.engine.execute(f"""
	SELECT d.FULL_NAME, d.NUMBER, p.* FROM PLAY_BY_PLAY p
	JOIN PLAYER_DIM d on d.PLAYER_KEY = p.BATTER_PLAYER_KEY
	WHERE BATTER_PLAYER_KEY in ({keys})
	"""))
	return render_template('printSprays.html', keys = keyList, plays = json.dumps([dict(s) for s in plays]))


@app.route('/about')
def about():
	return render_template('about.html')

@app.route('/faq')
def faq():
	return render_template('faq.html')


@app.route('/resetDB')
def reset():
	u = request.values.get('u','')
	db.session.commit()
	if u == 'u':
		db.engine.execute("UPDATE ALLOW_SCRAPE SET ALLOW = 1")
		db.session.commit()
	return render_template('index.html')

@app.route('/lastUpdate')
def lastUpdate():
	data = list(db.engine.execute("""SELECT * FROM ALLOW_SCRAPE"""))
	return json.dumps([dict(r) for r in data])

@app.route('/allPlays')
def allPlays():
	org = request.values.get('org', 'WashU')
	year = request.values.get('year', '2020')
	p = request.values.get('p', '')
	plays = list(db.engine.execute("""SELECT p.FULL_NAME NAME, t.NAME TEAM_NAME, pbp.* FROM PLAY_BY_PLAY pbp
	JOIN PLAYER_DIM p on p.PLAYER_KEY = pbp.BATTER_PLAYER_KEY
	JOIN TEAM_DIM t on t.TEAM_KEY = pbp.BATTER_TEAM_KEY
	ORDER BY t.NAME
	 """))

	playsORG = list(db.engine.execute(f"""SELECT p.FULL_NAME NAME, t.NAME TEAM_NAME, pbp.* FROM PLAY_BY_PLAY pbp
 	JOIN PLAYER_DIM p on p.PLAYER_KEY = pbp.BATTER_PLAYER_KEY
 	JOIN TEAM_DIM t on t.TEAM_KEY = pbp.BATTER_TEAM_KEY
	WHERE t.NAME = '{org}' and pbp.YEAR = {year}
 	ORDER BY t.NAME
 	 """))

	data = []
	for d in plays:
		play = {}
		play['date'] = d.DATE_KEY
		play['batter'] = d.NAME
		play['team'] = d.TEAM_NAME
		play['play'] = d.DESCRIPTION
		play['location'] = d.LOCATION
		play['outcome'] = d.OUTCOME
		play['active_record'] = d.ACTIVE_RECORD
		data.append(play)

	if p == 'p':
		return jsonify(data)

	return render_template('allPlays.html', plays = plays, playsJS = json.dumps([dict(r) for r in playsORG]))


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
