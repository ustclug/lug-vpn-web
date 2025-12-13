SQLALCHEMY_DATABASE_URI = 'mysql+mysqldb://radius:radius@localhost/radius?charset=utf8'
DEBUG = True
SECRET_KEY = 'secret-key'
# Optional: do NOT set this unless you need Flask to enforce a fixed host.
# If set, it MUST match the incoming Host header, otherwise Flask returns 404.
# SERVER_NAME = 'localhost:5000'
# SERVER_NAME = 'internet.zlix.tech'
SEND_FILE_MAX_AGE_DEFAULT = 3600

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