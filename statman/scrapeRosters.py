from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import sshtunnel
import MySQLdb
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from fuzzywuzzy import fuzz
import Levenshtein as lev
import gc
import time
import itertools

app = Flask(__name__)

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
		 'field':'14762'}

locations = ['1b', '2b', '3b', ' ss', ' p ', ' p.', ' p,',' p;', ' c ', ' c.', ' c,', 'catcher', 'pitcher',
' lf', ' rf', ' cf', 'shortstop', 'center',
'lcf', 'rcf',
'1b line', '3b line', 'left', 'right',
]

locMult = ['through the left side', 'through the right side', 'up the middle', 'left field line',
'right field line', 'left center', 'right center', 'third base', 'first base', 'second base',
'rf line', 'lf line']

outcomes = ['grounded','muffed','error','line','lined','flied','fly','force','pop','single','double','triple','home','choice','foul','bunt', 'out at']
outcomes2 = [' singled',' doubled',' tripled',' homer',' homered', ' reached', ' grounded',' muffed',' error',' line',' lined',' flied',' fly',' force',' pop',' single',' double',' triple',' home',' choice',' foul',' bunt',' bunted', ' out', ' out at']

unwanted = ['wild pitch', 'passed ball', ' balk ', 'picked off', 'caught stealing', ' struck ', ' walked ', ' stole ']


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

def date(text):
	text = str(text)
	if len(text) == 8:
		text = text[4:6] + '-' + text[6:8] + '-' + text[0:4]
	return text

def exists(text):
	if text is None:
		return '--'
	else:
		return text

def dist(a, b):
	dist = 0
	if len(a) > 3 and len(b) > 3:
		dist = fuzz.ratio(a.lower(),b.lower())/100
		dist2 = fuzz.partial_ratio(a.lower(),b.lower())
	else:
		return False
	if dist < 50 and dist2 < 50:
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


tunnel = sshtunnel.SSHTunnelForwarder(
    ('ssh.pythonanywhere.com'),
    ssh_username='StatmanSprays', ssh_password='Slayers11',
    remote_bind_address=('StatmanSprays.mysql.pythonanywhere-services.com', 3306)
)

tunnel.start()

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://StatmanSprays:GoBears!@127.0.0.1:{}/StatmanSprays$Slayer'.format(tunnel.local_bind_port)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_POOL_RECYCLE'] = 299

db = SQLAlchemy(app)

class team_dim(db.Model):
	__tablename__ = 'TEAM_DIM'

	TEAM_KEY = db.Column(db.Integer, primary_key=True)
	NAME = db.Column(db.String(50))
	ACTIVE_RECORD = db.Column(db.Integer)

	def __init__(self, key, name):
		self.TEAM_KEY = key
		self.NAME = name
		self.ACTIVE_RECORD = 1

class player_dim(db.Model):
	__tablename__ = 'PLAYER_DIM'

	PLAYER_KEY = db.Column(db.Integer, primary_key=True, autoincrement=True)
	NUMBER = db.Column(db.String(5))
	FULL_NAME = db.Column(db.String(50))
	POSITION = db.Column(db.String(5))
	CLASS = db.Column(db.String(20))
	YEAR = db.Column(db.String(5))
	TEAM_KEY = db.Column(db.Integer)
	ACTIVE_RECORD = db.Column(db.Integer)

	def __init__(self, num, name, pos, cl, y, tk):
		self.NUMBER = num
		self.FULL_NAME = name
		self.POSITION = pos
		self.CLASS = cl
		self.YEAR = y
		self.TEAM_KEY = tk
		self.ACTIVE_RECORD = 1


class hitter_stats(db.Model):
	__tablename__ = 'HITTER_STATS'

	FULL_NAME = db.Column(db.String(50), primary_key=True)
	POSITION = db.Column(db.String(5), primary_key=True)
	NUMBER = db.Column(db.String(5), primary_key=True)
	CLASS = db.Column(db.String(5), primary_key=True)
	YEAR = db.Column(db.Integer, primary_key=True)
	G = db.Column(db.Integer)
	GS = db.Column(db.Integer)
	AB = db.Column(db.Integer)
	BA = db.Column(db.Float)
	OBP = db.Column(db.Float)
	SLG = db.Column(db.Float)
	K = db.Column(db.Float)
	BB = db.Column(db.Float)
	SB = db.Column(db.Float)
	CS = db.Column(db.Float)
	IBB = db.Column(db.Float)
	HBP = db.Column(db.Float)
	SF = db.Column(db.Float)
	SH = db.Column(db.Float)
	R = db.Column(db.Float)
	RBI = db.Column(db.Float)
	TEAM_KEY = db.Column(db.Integer, primary_key=True)
	ACTIVE_RECORD = db.Column(db.Integer)

	def __init__(self, name, pos, num, cl, y, g, gs, ab, ba, obp, slg, k, bb, sb, cs, ibb, hbp, sf, sh, r, rbi, tk):
		self.FULL_NAME = name
		self.POSITION = pos
		self.NUMBER = num
		self.CLASS = cl
		self.YEAR = y
		self.G = g
		self.GS = gs
		self.AB = 0 if ab == '' else ab
		self.BA = ba
		self.OBP = obp
		self.SLG = slg
		self.K = 0 if k == '' else k
		self.BB = 0 if bb == '' else bb
		self.SB = 0 if sb == '' else sb
		self.CS = 0 if cs == '' else cs
		self.IBB = 0 if ibb == '' else ibb
		self.HBP = 0 if hbp == '' else hbp
		self.SF = 0 if sf == '' else sf
		self.SH = 0 if sh == '' else sh
		self.R = 0 if r == '' else r
		self.RBI = 0 if rbi == '' else rbi
		self.TEAM_KEY = tk
		self.ACTIVE_RECORD = 1

class play_by_play(db.Model):
	__tablename__ = 'PLAY_BY_PLAY'

	PLAY_ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
	DATE_KEY = db.Column(db.Integer)
	BATTER_PLAYER_KEY = db.Column(db.Integer)
	BATTER_TEAM_KEY = db.Column(db.Integer)
	PITCHER_TEAM_KEY = db.Column(db.Integer)
	OUTCOME = db.Column(db.String(50))
	LOCATION = db.Column(db.String(50))
	DESCRIPTION = db.Column(db.String(500))
	YEAR = db.Column(db.Integer)
	ACTIVE_RECORD = db.Column(db.Integer)

	def __init__(self, date, bpk, btk, ptk, out, loc, year, dec):
		self.DATE_KEY = date
		self.BATTER_PLAYER_KEY = bpk
		self.BATTER_TEAM_KEY = btk
		self.PITCHER_TEAM_KEY = ptk
		self.OUTCOME = out
		self.LOCATION = loc
		self.DESCRIPTION = dec
		self.YEAR = year
		self.ACTIVE_RECORD = 1

## scrape 2021 rosters
teams = list(db.engine.execute('SELECT * FROM TEAM_DIM'))
year = 2021
r = ''
for teamRow in teams[0:3]:
	if 1 == 1:
		rosterToAdd = []
		team = teamRow.TEAM_KEY
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
			print(f'no roster {team}')
			continue

		for player in rosterToAdd:
			db.session.add(player)
		db.session.commit()

		players = list(db.engine.execute(f"SELECT * FROM PLAYER_DIM WHERE YEAR = '{year}' and TEAM_KEY = {team}"))
		print(f'success {team} {len(players)} players')
	else:
		print(f'skipped {team}')
		continue

tunnel.close()
