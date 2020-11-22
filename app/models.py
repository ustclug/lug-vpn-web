from app import db
from flask_login import UserMixin
from app.utils import *
import hashlib
import datetime
import calendar


class Group(db.Model):
    __tablename__ = 'radusergroup'
    username = db.Column(db.String(64), primary_key=True)
    groupname = db.Column(db.String(64))
    priority = db.Column(db.Integer)

    def __init__(self, email, group='normal', priority=1):
        self.username = email
        self.groupname = group
        self.priority = priority

    def save(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_group_by_email(cls, email):
        return cls.query.filter_by(username=email).first()


class Record(db.Model):
    __tablename__ = 'radacct'
    radacctid = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64))
    acctstarttime = db.Column(db.DateTime())
    acctstoptime = db.Column(db.DateTime())
    callingstationid = db.Column(db.String(50))
    acctinputoctets = db.Column(db.BigInteger)
    acctoutputoctets = db.Column(db.BigInteger)
    framedipaddress = db.Column(db.String(15))


class VPNAccount(db.Model):
    __tablename__ = 'radcheck'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64))
    attribute = db.Column(db.String(64))
    op = db.Column(db.CHAR(2), default='==')
    value = db.Column(db.String(253))

    def __init__(self, username, value, is_expiration=False):
        self.username = username
        self.value = value
        self.attribute = 'Expiration' if is_expiration else 'SSHA2-256-Password'
        self.op = ':='

    def save(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_account_by_email(cls, email):
        return cls.query.filter_by(username=email).filter_by(attribute='SSHA2-256-Password').first()

    @classmethod
    def get_expiration_by_email(cls, email):
        return cls.query.filter_by(username=email).filter_by(attribute='Expiration').first()

    @classmethod
    def add(cls, email, password, expiration):
        account = cls.get_account_by_email(email)
        if not account:
            account = cls(email, hash_passwd(password.encode('utf-8')))
            account.save()
            if not Group.get_group_by_email(email):
                group = Group(email)
                group.save()
            cls.update_expiration(email, expiration)
        else:
            raise Exception('account already exist')

    @classmethod
    def update_expiration(cls, email, expiration):
        expiration_row = cls.get_expiration_by_email(email)
        if not expiration_row:
            expiration_row = cls(email, expiration.strftime('%d %b %Y'), True)
        else:
            expiration_row.value = expiration.strftime('%d %b %Y')
        expiration_row.save()

    @classmethod
    def delete(cls, email):
        account = cls.get_account_by_email(email)
        if account:
            db.session.delete(account)
            expiration = cls.get_expiration_by_email(email)
            if expiration:
                db.session.delete(expiration)
            group = Group.get_group_by_email(email)
            if group:
                db.session.delete(group)
            db.session.commit()
        else:
            raise Exception('account not found')

    @classmethod
    def changepass(cls, email, newpass):
        account = cls.get_account_by_email(email)
        if not account:
            raise Exception('account not found')
        else:
            account.value = hash_passwd(newpass.encode('utf-8'))
        account.save()


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(63), unique=True)
    passwordhash = db.Column(db.String(127), nullable=False)
    salt = db.Column(db.String(127), nullable=False)
    active = db.Column(db.Boolean(), default=False)
    admin = db.Column(db.Boolean(), default=False)
    status = db.Column(db.Enum('none', 'applying', 'pass', 'reject', 'banned'), default='none')
    name = db.Column(db.String(127))
    studentno = db.Column(db.String(127))
    phone = db.Column(db.String(127))
    reason = db.Column(db.Text)
    applytime = db.Column(db.DateTime)
    vpnpassword = db.Column(db.String(127))
    rejectreason = db.Column(db.Text)
    banreason = db.Column(db.Text)
    expiration = db.Column(db.Date)
    renewing = db.Column(db.Boolean(), default=False)

    def __init__(self, email, password):
        self.email = email
        self.set_password(password)

    def set_active(self):
        if VPNAccount.get_account_by_email(self.email):
            # existing vpn user
            self.status = 'pass'
            self.vpnpassword = VPNAccount.get_account_by_email(self.email).value
        self.active = True
        self.save()

    def set_password(self, password):
        self.salt = random_string(10)
        s = hashlib.sha256()
        s.update(password.encode('utf-8'))
        s.update(self.salt.encode('utf-8'))
        self.passwordhash = s.hexdigest()

    def check_password(self, password):
        s = hashlib.sha256()
        s.update(password.encode('utf-8'))
        s.update(self.salt.encode('utf-8'))
        return self.passwordhash == s.hexdigest()

    def enable_vpn(self):
        if not VPNAccount.get_account_by_email(self.email):
            if self.vpnpassword is None:
                self.generate_vpn_password()
            VPNAccount.add(self.email, self.vpnpassword, self.expiration)

    def disable_vpn(self):
        if VPNAccount.get_account_by_email(self.email):
            VPNAccount.delete(self.email)

    def change_vpn_password(self):
        self.generate_vpn_password()
        VPNAccount.changepass(self.email, self.vpnpassword)

    @classmethod
    def get_applying(cls):
        return cls.query.filter(db.or_(cls.status == 'applying', cls.renewing == True)).order_by(cls.applytime).all()

    @classmethod
    def get_applying_count(cls):
        return cls.query.filter(db.or_(cls.status == 'applying', cls.renewing == True)).count()

    @classmethod
    def get_rejected(cls):
        return cls.query.filter_by(status='reject').order_by(cls.applytime.desc()).all()

    @classmethod
    def get_users(cls):
        return cls.query.filter(db.or_(cls.status == 'pass', cls.status == 'banned')).order_by(cls.id).all()

    def vpnpassword_invisible(self):
        self.vpnpassword = "<secure>"
        self.save()

    def pass_apply(self):
        self.status = 'pass'
        self.expiration = next_semester_end()
        self.enable_vpn()
        self.save()

    def renew(self):
        self.expiration = next_semester_end()
        VPNAccount.update_expiration(self.email, self.expiration)
        self.save()

    def pass_renewal(self):
        self.renew()
        self.renewing = False
        self.save()

    def reject_apply(self, reason=''):
        self.status = 'reject'
        self.rejectreason = reason
        self.save()

    def reject_renewal(self, reason=''):
        self.rejectreason = reason
        self.renewing = False
        self.save()

    def ban(self, reason=''):
        self.status = 'banned'
        self.banreason = reason
        self.disable_vpn()
        self.save()

    def unban(self):
        self.status = 'pass'
        self.enable_vpn()
        self.save()

    def save(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_user_by_email(cls, email):
        return cls.query.filter_by(email=email).first()

    @classmethod
    def get_user_by_id(cls, id):
        return cls.query.get(id)

    def get_record(self):
        return Record.query.filter_by(username=self.email).order_by(Record.radacctid.desc()).first()

    def get_records(self, n):
        return Record.query.filter_by(username=self.email).order_by(Record.radacctid.desc()).limit(n)

    def generate_vpn_password(self):
        self.vpnpassword = random_string(8)
        self.save()

    def month_traffic(self):
        r = db.engine.execute('select TrafficSum from monthtraffic where UserName = %s', self.email).first()
        return sizeof_fmt(float(r[0]) if r else 0)

    def last_month_traffic(self):
        r = db.engine.execute('select TrafficSum from lastmonthtraffic where UserName = %s', self.email).first()
        return sizeof_fmt(float(r[0]) if r else 0)

    @classmethod
    def all_month_traffic(cls):
        r = db.engine.execute('select * from monthtraffic')
        return {row[0]: row[1] for row in r}

    @classmethod
    def all_last_month_traffic(cls):
        r = db.engine.execute('select * from lastmonthtraffic')
        return {row[0]: row[1] for row in r}

    def last_month_traffic_by_day(self):
        r = db.engine.execute("""
            select
                day(radius.radacct.acctstarttime) AS Day,
                sum(radius.radacct.acctinputoctets) AS Upload,
                sum(radius.radacct.acctoutputoctets) AS Download
            from
                radius.radacct
            where
                month(radius.radacct.acctstarttime) = month(date_sub(now(),interval 1 month)) and
                year(radius.radacct.acctstarttime) = year(date_sub(now(),interval 1 month)) and
                radius.radacct.username = %s
            group by
                day(radius.radacct.acctstarttime);
        """, self.email)
        lastmonth = datetime.datetime.now().replace(day=1) - datetime.timedelta(days=1)
        days = calendar.monthrange(lastmonth.year, lastmonth.month)[1]
        traffic = [(i, 0, 0) for i in range(1, days + 1)]
        for row in r:
            traffic[int(row[0]) - 1] = (int(row[0]), row[1], row[2])
        return traffic

    def month_traffic_by_day(self):
        r = db.engine.execute("""
            select
                day(radius.radacct.acctstarttime) AS Day,
                sum(radius.radacct.acctinputoctets) AS Upload,
                sum(radius.radacct.acctoutputoctets) AS Download
            from
                radius.radacct
            where
                month(radius.radacct.acctstarttime) = month(now()) and
                year(radius.radacct.acctstarttime) = year(now()) and
                radius.radacct.username = %s
            group by
                day(radius.radacct.acctstarttime);
        """, self.email)
        now = datetime.datetime.now()
        days = calendar.monthrange(now.year, now.month)[1]
        traffic = [(i, 0, 0) for i in range(1, days + 1)]
        for row in r:
            traffic[int(row[0]) - 1] = (int(row[0]), row[1], row[2])
        return traffic
