from importlib import import_module

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

app = Flask(__name__)
app.config.from_object('config.example')
try:
    operator_config = import_module('config.default')
except ModuleNotFoundError as exc:
    if exc.name != 'config.default':
        raise
else:
    app.config.from_object(operator_config)

app.jinja_env.globals['site_name'] = app.config['SITE_NAME']

db = SQLAlchemy(app)

from flask_bootstrap import Bootstrap

Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

from app.models import *


@login_manager.user_loader
def load_user(userid):
    return User.query.get(userid)


from app.views import *
