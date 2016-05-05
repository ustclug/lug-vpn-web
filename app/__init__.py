from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager

app=Flask(__name__)
app.config.from_object('config.default')

db=SQLAlchemy(app)

from flask_bootstrap import Bootstrap
Bootstrap(app)

login_manager=LoginManager()
login_manager.init_app(app)
login_manager.login_view='login'

from app.models import *

@login_manager.user_loader
def load_user(userid):
    return User.query.get(userid)

from app.views import *
