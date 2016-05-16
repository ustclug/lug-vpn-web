from app import db
from flask.ext.login import UserMixin

class Record(db.Model):
    __tablename__='radacct'
    radacctid=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(64))
    acctstarttime=db.Column(db.DateTime())
    acctstoptime=db.Column(db.DateTime())
    callingstationid=db.Column(db.String(50))

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
        account=cls.query.filter_by(username=user.email).first()
        if not account:
            account=cls(user.email,user.password)
        else:
            account.value=user.password
        account.save()

    @classmethod
    def get_all(cls):
        return cls.query.all()

    def get_record(self):
        return Record.query.filter_by(username=self.username).order_by(Record.radacctid.desc()).first()

class User(db.Model,UserMixin):
    __tablename__='user'
    id=db.Column(db.Integer,primary_key=True)
    email=db.Column(db.String(63),unique=True)
    password=db.Column(db.String(127),nullable=False)
    active=db.Column(db.Boolean(),default=False)
    admin=db.Column(db.Boolean(),default=False)
    apply=db.Column(db.Enum('none','applying','pass','reject'),default='none')
    name=db.Column(db.String(127))
    studentno=db.Column(db.String(127))
    phone=db.Column(db.String(127))
    address=db.Column(db.String(127))
    reason=db.Column(db.Text)
    applytime=db.Column(db.DateTime)

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

    def get_record(self):
        return Record.query.filter_by(username=self.email).order_by(Record.radacctid.desc()).first()

