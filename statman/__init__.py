from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

app = Flask(__name__)
from statman.config import Config
app.config.from_object(Config)

db = SQLAlchemy(app)

from statman import views, models

from statman.models import User

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_message = "Please log in to access that page."
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
	return User.query.filter_by(USER_KEY=int(user_id)).first()
