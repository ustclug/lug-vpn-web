from app import db, redis_conn, influxdb_conn
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
        self.attribute = 'Expiration' if is_expiration else 'Cleartext-Password'
        self.op = ':='

    def save(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_account_by_email(cls, email):
        return cls.query.filter_by(username=email).filter_by(attribute='Cleartext-Password').first()

    @classmethod
    def get_expiration_by_email(cls, email):
        return cls.query.filter_by(username=email).filter_by(attribute='Expiration').first()

    @classmethod
    def add(cls, email, password, expiration):
        account = cls.get_account_by_email(email)
        if not account:
            account = cls(email, password)
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
            account.value = newpass
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

    def set_expiration(self, expiration, delete=False):
        self.expiration = expiration
        redis_conn.hset(f"user:{self.email}", "Expiration", expiration)
        if VPNAccount.get_account_by_email(self.email):
            if delete:
                VPNAccount.delete(self.email)
            else:
                VPNAccount.update_expiration(self.email, expiration)

    def pass_apply(self):
        self.status = 'pass'
        self.expiration = next_school_year_end()
        self.enable_vpn()
        self.save()

    def renew(self):
        self.set_expiration(next_school_year_end())
        self.save()

    def pass_renewal(self):
        self.renew()
        self.renewing = False
        self.save()

    def reject(self, reason='', expiration=None, force=False):
        self.rejectreason = reason
        self.set_expiration(expiration or this_school_year_end(), delete=force)
        self.renewing = False
        if force or self.status != 'pass':
            self.status = 'reject'
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
        month_start, month_end = get_month_timestamps()
        r = influxdb_conn.query(f"""
        SELECT sum('bytes') AS bytes WHERE ("user" = '$email') AND time >= {month_start} AND time <= {month_end}
        """, bind_params={'email': self.email})
        # TODO
        return sizeof_fmt(float(r[0]) if r and r[0] else 0)

    def last_month_traffic(self):
        last_month_start, last_month_end = get_last_month_timestamps()
        r = influxdb_conn.query(f"""
        SELECT sum('bytes') AS bytes WHERE ("user" = '$email') AND time >= {last_month_start} AND time <= {last_month_end}
        """, bind_params={'email': self.email})
        return sizeof_fmt(float(r[0]) if r and r[0] else 0)

    @classmethod
    def all_month_traffic(cls):
        month_start, month_end = get_month_timestamps()
        r = influxdb_conn.query(f"""
        SELECT sum('bytes') AS bytes WHERE time >= {month_start} AND time <= {month_end} GROUP BY "user"
        """)
        return {row[0]: row[1] for row in r}

    @classmethod
    def all_last_month_traffic(cls):
        last_month_start, last_month_end = get_last_month_timestamps()
        r = influxdb_conn.query(f"""
        SELECT sum('bytes') AS bytes WHERE time >= {last_month_start} AND time <= {last_month_end} GROUP BY "user"
        """)
        return {row[0]: row[1] for row in r}

    def last_month_traffic_by_day(self):
        last_month_start, last_month_end = get_last_month_timestamps()
        r = influxdb_conn.query(f"""
        SELECT sum('bytes') AS bytes WHERE ("user" = '$email') AND time >= {last_month_start} AND time <= {last_month_end} GROUP BY time(1d)
        """, bind_params={'email': self.email})
        # TODO: no upload/download diff?
        traffic = [(i, row[1], row[1]) for i, row in enumerate(r)]
        return traffic


    def month_traffic_by_day(self):
        month_start, month_end = get_month_timestamps()
        r = influxdb_conn.query(f"""
        SELECT sum('bytes') AS bytes WHERE ("user" = '$email') AND time >= {month_start} AND time <= {month_end} GROUP BY time(1d)
        """, bind_params={'email': self.email})
        traffic = [(i, row[1], row[1]) for i, row in enumerate(r)]
        return traffic
