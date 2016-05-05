from app import db
from flask.ext.login import UserMixin

class VPNAccount(db.Model):
    __tablename__='radcheck'
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(64))
    attribute=db.Column(db.String(64))
    op=db.Column(db.CHAR(2),default='==')
    value=db.Column(db.String(253))

    def __init__(self,username,password):
        self.username=username
        self.value=password
        self.attribute='Cleartext-Password'
        self.op=':='

    def save(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def add(cls,user):
        account=cls(user.email,user.password)
        account.save()

class User(db.Model,UserMixin):
    __tablename__='user'
    id=db.Column(db.Integer,primary_key=True)
    email=db.Column(db.String(63),unique=True)
    password=db.Column(db.String(127),nullable=False)
    active=db.Column(db.Boolean(),default=False)
    admin=db.Column(db.Boolean(),default=False)
    apply=db.Column(db.Enum('none','applying','pass','reject'),default='none')

    def __init__(self,email,password):
        self.email=email
        self.password=password

    @classmethod
    def get_applying(cls):
        return cls.query.filter_by(apply='applying').all()

    def pass_apply(self):
        self.apply='pass'
        self.save()
        VPNAccount.add(self)

    def reject_apply(self):
        self.apply='reject'
        self.save()

    def save(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_user_by_email(cls,email):
        return cls.query.filter_by(email=email).first()

    @classmethod
    def get_user_by_id(cls,id):
        return cls.query.get(id)

