SQLALCHEMY_DATABASE_URI = 'mysql+mysqldb://radius:radius@localhost/radius?charset=utf8'
DEBUG = True
SECRET_KEY = 'secret-key'
SERVER_NAME = 'localhost:5000'

MAIL_ENABLE = False
MAIL_SERVER = 'localhost'
MAIL_PORT = 25
MAIL_USE_TLS = False
MAIL_USE_SSL = False
MAIL_USERNAME = ''
MAIL_PASSWORD = ''
MAIL_DEFAULT_SENDER = ''
ADMIN_MAIL = 'lug@ustc.edu.cn'

BOOTSTRAP_SERVE_LOCAL = True

SQLALCHEMY_TRACK_MODIFICATIONS = False

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_USERNAME = None
REDIS_PASSWORD = None
INFLUXDB_HOST = "localhost"
INFLUXDB_PORT = 8086
INFLUXDB_USERNAME = "root"
INFLUXDB_PASSWORD = "root"
INFLUXDB_DATABASE = "light"
