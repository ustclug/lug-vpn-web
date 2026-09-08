SQLALCHEMY_DATABASE_URI = 'mysql+mysqldb://radius:radius@localhost/radius?charset=utf8'
DEBUG = True
SECRET_KEY = 'secret-key'
SERVER_NAME = 'localhost:5000'
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

# Deployment branding and optional application features.
SITE_NAME = 'LUG VPN'
APPLICATION_REASONS = []
LIBRARY_API_URL = None
LIBRARY_API_TIMEOUT = 5

# Filenames are relative to app/doc. Operators should mount that directory.
CONSTITUTION_DOCUMENTS = [
    ('Constitution', 'constitution.md'),
]
TERMS_DOCUMENTS = []
APPLICATION_CONFIRMATION_ENABLED = False
