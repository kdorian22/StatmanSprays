from functools import wraps
import requests
import pandas as pd
from bs4 import BeautifulSoup
import numpy as np
import re
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz
import Levenshtein as lev
import gc
import time
import itertools
import json
from sqlalchemy import text

divDict = {
'2025': ['18543', '18544', '18545'],
'2024': ['18300', '18301', '18302'],
'2023': ['18080', '18082', '18083'],
'2022': ['17760', '17761', '17762'],
'2021': ['17500', '17501', '17502'],
'2020': ['17126', '17127', '17128'],
'2019': ['16800', '16801', '16802'],
'2018': ['14211', '14212', '14213']
}

yearCodes = {
		 '2025': '16840',
		 '2024': '16580',
		 '2023': '16340',
		 '2022': '15860',
		 '2021': '15580',
		 '2020': '15204',
		 '2019': '14781',
		 '2018': '12973',
		 '2017': '12560',
		 '2016': '12360'
		}

years = ['2025', '2024', '2023', '2022', '2021', '2020', '2019', '2018']

locations = ['1b', '2b', '3b', ' ss', ' p ', ' p.', ' p,',' p;', ' p:', ' c ', ' c.', ' c,', ' c;', 'catcher', 'pitcher',
' lf', ' rf', ' cf', 'shortstop', 'center', 'lcf', 'rcf', '1b line', '3b line', ' left', ' right',
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


unwanted = ['wild pitch', 'passed ball', ' balk.', ' balk ', 'picked off', 'pickoff', 'caught stealing', ' struck ', ' walked ', ' walked.', ' stole ']
mistakes = ['advanced', 'advances', 'advnace', 'scored', 'scores', 'score']

def scrapeTeams():
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
	return teamList

## Levenshtein Distance -- https://towardsdatascience.com/fuzzywuzzy-how-to-measure-string-distance-on-python-4e8852d7c18f
def dist(a, b):
	dist = 0
	if len(a) > 3 and len(b) > 3:
		dist = fuzz.ratio(a.lower(),b.lower())/100
		dist2 = fuzz.partial_ratio(a.lower(),b.lower())
	else:
		return False
	if dist < .50 and dist2 < 50:
		return False
	if dist >= (max([len(a), len(b)])-2)/max([len(a), len(b)]) or dist2 == 100:
		return True
	else:
		return False



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

def getRoster(teamYearId, player_dim, team, year):
	url=f'https://stats.ncaa.org/teams/{teamYearId}/roster'
	soup = BeautifulSoup(requests.get(url, headers = {"User-Agent": "Mozilla/5.0"}).content, 'lxml')
	table = soup.find('tbody')

	rosterToAdd = []
	if table is not None:
		for row in table.findAll('tr'):
			cells = []
			for cell in row.findAll('td'):
				text = cell.text.replace("\n", '')
				text = cell.text.replace('nbsp&', '')
				cells.append(text)
			fullName = cells[3]
			if ', ' not in fullName:
				name = fullName.split(' ', 1)
				if len(name) > 1:
					lastName = name[1]
					firstName = name[0]
					fullName = lastName + ', ' +  firstName				
			rosterToAdd.append(player_dim(cells[2], fullName.replace('â€™',"'"), cells[5], cells[4], year, team, cells[7], cells[8]))
	return rosterToAdd

def scrapeRoster(team, year, db, player_dim, team_id_lk):
	try:
		existingRoster = player_dim.query.filter_by(YEAR=str(year)).filter_by(TEAM_KEY=team).all()
		players = [[x.FULL_NAME, x.NUMBER, x.CLASS] for x in existingRoster]
		teamYearId = team_id_lk.query.filter_by(TEAM_ID=team).filter_by(YEAR=str(year)).first()
		rosterToAdd = getRoster(teamYearId.TEAM_SEASON_ID, player_dim, team, year)
		for player in rosterToAdd:
			if [player.FULL_NAME, player.NUMBER, player.CLASS] not in players:
				db.session.merge(player)
				db.session.commit()

		with db.engine.connect() as conn:
			players = list(conn.execute(text(f"SELECT * FROM PLAYER_DIM WHERE YEAR = '{year}' and TEAM_KEY = {team}")).fetchall())
			db.session.commit()

		return players
	except:
		print(f'error encountered on {team} roster scrape')
		return []

# gameParser takes in several parameters pertaining to the game, search team, and alternate team name list
def gameParser(soup, players, teamNameList, altNames, altTeamNameList, team_dim, team, roster):
	allPlays = []
	plays = []
	try:
		date = soup.find('td', class_='d-md-table-cell').findAll('tr')[3].find('td').text.strip()[0:10]
		date = date[6:10] + date[0:2] + date[3:5]
	except:
		date = None

	## Plays are stored in a 3-column table. This is how we identify which column we want
	index = 10
	for i, td in enumerate(soup.find('table', class_="table").findAll('th')):
		if td.text not in teamNameList and td.text != 'Score':
			oppTeamName = td.text
			if oppTeamName in altNames:
				oppTeamName = [x.NAME for x in altTeamNameList if td.text in x.ALT_NAMES][0]
		if td.text in teamNameList or bool([x for x in teamNameList if td.text in x.split()]):
			index = i
	if index < 10:
		oppTeam = team_dim.query.filter_by(NAME=oppTeamName).first()
		if oppTeam != None:
			ptk = oppTeam.TEAM_KEY
		else:
			ptk = None


		for table in soup.findAll('table', class_="table"):
			tbody = table.find('tbody')
			for play in tbody.findAll('tr'):
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
					if bool([pl for pl in players[p.PLAYER_KEY] if(dist(pl,start.split(' ')[0].replace(',','')))]):
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


			if len([t for t in mistakes if(t in start)]) > 0 and len([t for t in outcomes+outcomes2 if(t in play)]) == 0:
				play_details['outcome'] = None
			allPlays.append(play_details)
	return allPlays

def jsonDump(data):
	return json.dumps([dict(d) for d in data])

# Get list of box score links for a give date/division
def getBoxLinks(div, year, month, day):
	direct = []
	try:
		url = f"https://stats.ncaa.org/contests/scoreboards?season_division_id={div}&game_date={month}%2F{day}%2F{year}"
		soup = BeautifulSoup(requests.get(url, headers = {"User-Agent": "Mozilla/5.0"}).content, 'html.parser')
		pageDate = soup.select('input#game_date')[0]['value'].split('/')
		compDate = [month, day, year]
		if compDate == pageDate:
			for link in soup.findAll('a', attrs={'href': re.compile("^/contests"), 'target': re.compile("box")}):
				direct.append(link.get('href'))
	except:
		direct = []
	return direct

# Get anchor linking to the PBP from box score link (available in GAME_DIM)
def getPBPElement(box):
	try:
		boxLink = f"https://stats.ncaa.org{box}"
		soup = BeautifulSoup(requests.get(boxLink, headers = {"User-Agent": "Mozilla/5.0"}).content, 'lxml')
		element = soup.find('a', attrs={'href': re.compile("/play_by_play")})
	except:
		element = None
	return element


def getRosterNames(roster):
	players = {}
	## For each guy on the roster, list the different ways his name can be stored and return as dict
	for r in roster:
		try:
			names = []
			full = r.FULL_NAME
			if ', ' in full :
				full = full.split(', ')
			else:
				full = full.split(' ', 1)[::-1]
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
				names.append(full[0])
				if "'" in r.FULL_NAME:
					names.append(r.FULL_NAME.replace("'",'').replace("'",''))
					names.append(full[0].replace("'",'').replace("'",''))
				if len(last) == 2:
					names.append(last[0][0] + '. ' + last[1])
					names = names + [x.upper() for x in names]
			else:
				names = []
		except:
			names = []
		players[r.PLAYER_KEY] = names
	return players


def getMatchup(pbp, altNames, altTeamNameList):
	try:
		pbpSoup = BeautifulSoup(requests.get(pbp, headers = {"User-Agent": "Mozilla/5.0"}).content, 'lxml')
		teams = []
		for i, td in enumerate(pbpSoup.find('table', class_="table").findAll('th')):
			if td.text != 'Score':
				if td.text in altNames:
					listedName = [x.NAME for x in altTeamNameList if td.text in x.ALT_NAMES][0]
					teams.append(listedName)
				else:
					teams.append(td.text)
	except:
		teams = []

	return teams, pbpSoup

def updateHitterStats(year, team, hitter_stats, db):
	url=f'https://stats.ncaa.org/team/{team}/stats/{yearCodes[str(year)]}'
	soup = BeautifulSoup(requests.get(url, headers = {"User-Agent": "Mozilla/5.0"}).content, 'html.parser')
	table = soup.find('tbody')
	if table is not None:
		rosterToAdd = []
		if table is not None:
			for row in table.findAll('tr'):
				cells = []
				for cell in row.findAll('td'):
					text = cell.text.replace("\n", '')
					text = cell.text.replace('nbsp&', '')
					cells.append(text)
				
				# name
				fullName = cells[1]
				if ', ' not in fullName:
					name = fullName.split(' ', 1)
					if len(name) > 1:
						lastName = name[1]
						firstName = name[0]
						fullName = lastName + ', ' +  firstName		
				rosterToAdd.append(hitter_stats(fullName.replace('â€™',"'").replace("\n", '').strip(),
				# position
				cells[3].replace("\n", '').strip(),
				# jersey
				cells[0].replace("\n", '').strip(),
				# class
				cells[2].replace("\n", '').strip(),
				year,
				# games
				cells[6].replace("\n", '').strip(),
				# games started
				cells[7].replace("\n", '').strip(),
				# AB
				cells[12].replace("\n", '').strip(),
				# BA
				cells[8].replace("\n", '').strip(),
				# OBP
				cells[9].replace("\n", '').strip(),
				#SLG
				cells[10].replace("\n", '').strip(),
				#K
				cells[23].replace("\n", '').strip(),
				#BB
				cells[19].replace("\n", '').strip(),
				#SB
				cells[27].replace("\n", '').strip(),
				#CS
				cells[25].replace('\n', '').strip(),
				# IBB
				cells[28].replace('\n', '').strip(),
				# HBP
				cells[20].replace("\n", '').strip(),
				#SF
				cells[21].replace("\n", '').strip(),
				#SH
				cells[22].replace("\n", '').strip(),
				#R
				cells[11].replace("\n", '').strip(),
				#RBI
				cells[18].replace("\n", '').strip(),

				team))
		lastName = ''
		lastNum = ''
		for player in rosterToAdd:
			# handle duplicate roster entries
			name = player.FULL_NAME
			num = player.NUMBER
			try:
				if name != lastName and num != lastNum:
					pass
					db.session.merge(player)
			except:
				continue
			lastName = player.FULL_NAME
			lastNum = player.NUMBER
	db.session.commit()
	return True

def getScoreVal(val):
	if len(val) > 0:
		return val[0].text.strip()
	else:
		return None

def getTeamName(val):
	if len(val) > 0:
		text = re.sub("""\(([0-90\-\0-90)]+)\)""", '', val[0].text.strip()).strip()
		text = re.sub("""\#?\d+""", '', text).strip()
		return text
	else:
		return None
	
def getTeamIdFromLink(val, team_id_lk):
	try:
		if len(val) > 0:
			teamSeasonId = val.get('href').split('/')[2]
			row = team_id_lk.query.filter_by(TEAM_SEASON_ID=teamSeasonId).first()
			if row is not None:
				return row.TEAM_ID
			else:
				return None
		else:
			return None
	except:
		return None

def getLink(row):
	try:
		cont = row.findAll('a', attrs={'href': re.compile("^/contests"), 'target': re.compile("box")})
		if len(cont) > 0:
			return f"https://stats.ncaa.org{cont[0].get('href')}"
		else:
			return None
	except:
		return None

def getTeamKey(teamName, team_dim, altNames, altTeamNameList):
	if teamName is not None:
		try:
			teamKey = team_dim.query.filter_by(NAME=teamName).first()
			if teamKey is not None:
				return teamKey.TEAM_KEY
			elif teamName in altNames:
				teamKey = [x.TEAM_KEY for x in altTeamNameList if teamName in x.ALT_NAMES][0]
				if teamKey is not None:
					return teamKey.TEAM_KEY
		except:
			return None
	else:
		return None


def getSchedule(year, month, day, div, divList, game_dim, team_id_lk, db):
	games = []
	url = f"https://stats.ncaa.org/contests/scoreboards?season_division_id={div}&game_date={month}%2F{day}%2F{year}"
	soup = BeautifulSoup(requests.get(url, headers = {"User-Agent": "Mozilla/5.0"}).content, 'lxml')
	pageDate = soup.select('input#game_date')[0]['value'].split('/')
	compDate = [month, day, year]
	dbDate = year+month+day
	if compDate == pageDate:
		print(f"Yes D{divList.index(div)+1} Games On {month+'/'+day+'/'+year}")
		games = soup.findAll('a', attrs={'href': re.compile("^/contests"), 'target': re.compile("box")})
		rows = soup.select('tbody > tr')
		print(f"{len(games)} D{divList.index(div)+1} Games On {month+'/'+day+'/'+year}")
		for i in range(0, len(games)):
			try:
				rowNum = i
				rows[rowNum*3].select('td a.skipMask')
				away_team = getTeamName(rows[rowNum*3].select('td a.skipMask'))
				away_score = getScoreVal(rows[rowNum*3].select('td.totalcol'))
				home_team = getTeamName(rows[rowNum*3+1].select('td a.skipMask'))
				home_score = getScoreVal(rows[rowNum*3+1].select('td.totalcol'))
				boxLink = getLink(rows[rowNum*3+2])
				home_key = getTeamIdFromLink(rows[rowNum*3].select('td a.skipMask'), team_id_lk)
				away_key = getTeamIdFromLink(rows[rowNum*3+1].select('td a.skipMask'), team_id_lk)
				newGame = game_dim(dbDate, year, home_key, home_team, away_key, away_team, home_score, away_score, boxLink)
				db.session.add(newGame)
			except:
				print(f'Broke on {dbDate} D{divList.index(div)+1}')
				continue
	else:
		print(f"No D{divList.index(div)+1} Games On {month+'/'+day+'/'+year}")
	db.session.commit()
	return True
