from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

app = Flask(__name__)
app.config.from_object('config.default')

db = SQLAlchemy(app)

import redis
import influxdb

redis_conn = redis.Redis(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'])
influxdb_conn = influxdb.InfluxDBClient(host=app.config['INFLUXDB_HOST'],
                                        port=app.config['INFLUXDB_PORT'],
                                        username=app.config['INFLUXDB_USERNAME'],
                                        password=app.config['INFLUXDB_PASSWORD'],
                                        database=app.config['INFLUXDB_DATABASE'])

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
