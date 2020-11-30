from statman import db


class team_dim(db.Model):
    __tablename__ = 'TEAM_DIM'

    TEAM_KEY = db.Column(db.Integer, primary_key=True)
    NAME = db.Column(db.String)
    ACTIVE_RECORD = db.Column(db.Integer)

class player_dim(db.Model):
    __tablename__ = 'PLAYER_DIM'

    PLAYER_KEY = db.Column(db.Integer, primary_key=True, autoincrement=True)
    NUMBER = db.Column(db.String)
    FULL_NAME = db.Column(db.String)
    POSITION = db.Column(db.String)
    CLASS = db.Column(db.String)
    YEAR = db.Column(db.String)
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

    FULL_NAME = db.Column(db.String, primary_key=True)
    POSITION = db.Column(db.String, primary_key=True)
    NUMBER = db.Column(db.String, primary_key=True)
    CLASS = db.Column(db.String, primary_key=True)
    YEAR = db.Column(db.Integer, primary_key=True)
    G = db.Column(db.Integer)
    GS = db.Column(db.Integer)
    BA = db.Column(db.Float)
    OBP = db.Column(db.Float)
    SLG = db.Column(db.Float)
    K = db.Column(db.Integer)
    BB = db.Column(db.Integer)
    SB = db.Column(db.Integer)
    CS = db.Column(db.Integer)
    TEAM_KEY = db.Column(db.Integer, primary_key=True)
    ACTIVE_RECORD = db.Column(db.Integer)

    def __init__(self, name, pos, num, cl, y, g, gs, ba, obp, slg, k, bb, sb, cs, tk):
        self.FULL_NAME = name
        self.POSITION = pos
        self.NUMBER = num
        self.CLASS = cl
        self.YEAR = y
        self.G = g
        self.GS = gs
        self.BA = ba
        self.OBP = obp
        self.SLG = slg
        self.K = k
        self.BB = bb
        self.SB = sb
        self.CS = cs
        self.TEAM_KEY = tk
        self.ACTIVE_RECORD = 1

class play_by_play(db.Model):
    __tablename__ = 'PLAY_BY_PLAY'

    PLAY_ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    DATE_KEY = db.Column(db.Integer)
    BATTER_PLAYER_KEY = db.Column(db.Integer)
    BATTER_TEAM_KEY = db.Column(db.Integer)
    PITCHER_TEAM_KEY = db.Column(db.Integer)
    OUTCOME = db.Column(db.String)
    LOCATION = db.Column(db.String)
    DESCRIPTION = db.Column(db.String)
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
