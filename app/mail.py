from . import app
from flask_mail import Mail,Message
import sys

mail = Mail(app)

def send_mail(subject,html,email):
    if app.config['MAIL_ENABLE']:
        msg = Message(subject=subject, html=html, recipients=[email])
        mail.send(msg)
    print('TO:',email, file=sys.stderr)
    print('Subject:',subject, file=sys.stderr)
    print('Html:',html, file=sys.stderr)

