from statman import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = 'USER_DIM'

    USER_KEY = db.Column(db.Integer, primary_key=True, autoincrement=True)
    EMAIL = db.Column(db.String(100), unique=True)
    PASSWORD = db.Column(db.String(100))
    NAME = db.Column(db.String(100))
    ADMIN = db.Column(db.Integer)
    ACTIVE_RECORD = db.Column(db.Integer)

    def __init__(self, email, name, password):
        self.EMAIL = email
        self.NAME = name
        self.PASSWORD = password
        self.ADMIN = 0
        self.ACTIVE_RECORD = 1

    def get_id(self):
           return (self.USER_KEY)

class team_dim(db.Model):
    __tablename__ = 'TEAM_DIM'

    TEAM_KEY = db.Column(db.Integer, primary_key=True)
    NAME = db.Column(db.String(50))
    VISITS = db.Column(db.Integer)
    ACTIVE_RECORD = db.Column(db.Integer)

    def __init__(self, key, name):
        self.TEAM_KEY = key
        self.NAME = name
        self.VISITS = 0
        self.ACTIVE_RECORD = 1

class game_dim(db.Model):
    __tablename__ = 'GAME_DIM'

    GAME_KEY = db.Column(db.Integer, primary_key=True, autoincrement=True)
    DATE_KEY = db.Column(db.Integer)
    YEAR = db.Column(db.Integer)
    HOME_TEAM_KEY = db.Column(db.Integer)
    AWAY_TEAM_KEY = db.Column(db.Integer)
    HOME_TEAM_SCORE = db.Column(db.Integer)
    AWAY_TEAM_SCORE = db.Column(db.Integer)
    PLAY_BY_PLAY = db.Column(db.Integer)
    ACTIVE_RECORD = db.Column(db.Integer)

    def __init__(self, dk, year, htk, atk, hts, ats, pbp):
        self.DATE_KEY = dk
        self.YEAR = year
        self.HOME_TEAM_KEY = htk
        self.AWAY_TEAM_KEY = atk
        self.HOME_TEAM_SCORE = hts
        self.AWAY_TEAM_SCORE = ats
        self.PLAY_BY_PLAY = pbp
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

    def __init__(self, date, bpk, btk, ptk, out, loc, dec, year):
        self.DATE_KEY = date
        self.BATTER_PLAYER_KEY = bpk
        self.BATTER_TEAM_KEY = btk
        self.PITCHER_TEAM_KEY = ptk
        self.OUTCOME = out
        self.LOCATION = loc
        self.DESCRIPTION = dec
        self.YEAR = year
        self.ACTIVE_RECORD = 1
