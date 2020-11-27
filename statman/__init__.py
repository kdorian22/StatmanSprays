from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
from statman.config import Config
app.config.from_object(Config)

db = SQLAlchemy(app)

from statman import views, models
