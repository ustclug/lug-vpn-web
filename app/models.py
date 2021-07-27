from typing import List
from app import db, redis_conn, influxdb_conn
from flask_login import UserMixin
from app.utils import *
import hashlib
import datetime
from dataclasses import dataclass
from dateutil import parser as isodate_parser  # handling ISO 8601 datetime str
from collections import defaultdict


@dataclass
class Record:
    """
    The record stored in influxdb
    """
    username: str
    dt: datetime.datetime
    bytes: int
    target: str
    duration: float
    client_addr: str

    def __init__(self, username, dt, bytes, target, duration, client_addr):
        self.username = username
        self.dt = dt
        self.bytes = int(bytes)
        self.target = target
        self.duration = duration
        self.client_addr = client_addr

        if 'Z' in self.dt:
            # ISO 8601
            self.dt = isodate_parser.parse(self.dt)
        if isinstance(self.dt, datetime.datetime):
            self.dt = self.dt.strftime("%Y/%m/%d %H:%M:%S")

    @classmethod
    def get_records(cls, username: str, n: int) -> List["Record"]:
        # TODO:
        # records are directly shown in user page
        # needs to be fixed
        if not isinstance(n, int):
            raise ValueError(f"{n} is not an integer.")
        res = influxdb_conn.query(f'select * from "light" where ("user" = $username) order by desc limit {n}', bind_params={
            'username': username
        }).get_points()
        return [Record(
            username=i['user'],
            dt=i['time'],
            bytes=i['bytes'],
            target=i['target'],
            duration=i['duration'],
            client_addr=i['client_addr']
        ) for i in res]


@dataclass
class VPNAccount:
    """
    The account stored in Redis.
    """
    username: str
    expiration: str
    clear_password: str

    def __init__(self, username, expiration, clear_password):
        self.username = username
        self.expiration = expiration
        self.clear_password = clear_password

    @classmethod
    def get_account_by_email(cls, email) -> "VPNAccount":
        vpnuser_info: dict = redis_conn.hgetall(f'user:{email}')
        if not vpnuser_info:
            return None
        return VPNAccount(
            username=email,
            expiration=vpnuser_info['Expiration'],
            clear_password=vpnuser_info['Cleartext-Password']
        )

    @classmethod
    def get_expiration_by_email(cls, email) -> int:
        vpnuser_info: dict = redis_conn.hgetall(f'user:{email}')
        if not vpnuser_info:
            return None
        return vpnuser_info['Expiration']

    @classmethod
    def add(cls, email, password, expiration):
        account = cls.get_account_by_email(email)
        if not account:
            redis_conn.hset(f'user:{email}', 'Cleartext-Password', password)
            redis_conn.hset(f'user:{email}', 'Data-Plan', 21474836480)  # 20GiB
            cls.update_expiration(email, expiration)
        else:
            raise Exception('account already exist')

    @classmethod
    def update_expiration(cls, email, expiration):
        redis_conn.hset(f'user:{email}', 'Expiration', expiration.strftime('%s'))

    @classmethod
    def delete(cls, email):
        account = cls.get_account_by_email(email)
        if account:
            redis_conn.delete(f'user:{email}')
        else:
            raise Exception('account not found')

    @classmethod
    def changepass(cls, email, newpass):
        account = cls.get_account_by_email(email)
        if not account:
            raise Exception('account not found')
        else:
            redis_conn.hset(f'user:{email}', 'Cleartext-Password', newpass)


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
        redis_conn.hset(f"user:{self.email}", "Expiration", expiration.strftime("%s"))
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
    def get_user_by_email(cls, email) -> 'User':
        return cls.query.filter_by(email=email).first()

    @classmethod
    def get_user_by_id(cls, id):
        return cls.query.get(id)

    def get_records(self, n):
        return Record.get_records(username=self.email, n=n)

    def generate_vpn_password(self):
        self.vpnpassword = random_string(8)
        self.save()

    def month_traffic(self):
        month_start, next_month_start = get_month_timestamps()
        r = influxdb_conn.query(f"""
        SELECT sum("bytes") AS bytes FROM light WHERE ("user" = $email) AND time >= $month_start AND time < $next_month_start
        """, bind_params={'email': self.email, 'month_start': month_start, 'next_month_start': next_month_start}).get_points()
        bytes = sum([i['bytes'] for i in r])
        return sizeof_fmt(float(bytes))

    def last_month_traffic(self):
        last_month_start, month_start = get_last_month_timestamps()
        r = influxdb_conn.query(f"""
        SELECT sum("bytes") AS bytes FROM light WHERE ("user" = $email) AND time >= $last_month_start AND time < $month_start
        """, bind_params={'email': self.email, 'last_month_start': last_month_start, 'month_start': month_start}).get_points()
        bytes = sum([i['bytes'] for i in r])
        return sizeof_fmt(float(bytes))

    @classmethod
    def all_month_traffic(cls):
        month_start, next_month_start = get_month_timestamps()
        r = influxdb_conn.query(f"""
        SELECT sum("bytes") AS bytes FROM light WHERE time >= $month_start AND time < $next_month_start GROUP BY "user"
        """, bind_params={'month_start': month_start, 'next_month_start': next_month_start})
        data = defaultdict(int)
        for key in r.keys():
            for i in r[key]:
                data[key[1]['user']] += i['bytes']
        return dict(data)

    @classmethod
    def all_last_month_traffic(cls):
        last_month_start, month_start = get_last_month_timestamps()
        r = influxdb_conn.query(f"""
        SELECT sum("bytes") AS bytes FROM light WHERE time >= $last_month_start AND time < $month_start GROUP BY "user"
        """, bind_params={'last_month_start': last_month_start, 'month_start': month_start})
        data = defaultdict(int)
        for key in r.keys():
            for i in r[key]:
                data[key[1]['user']] += i['bytes']
        return dict(data)

    def last_month_traffic_by_day(self):
        last_month_start, month_start = get_last_month_timestamps()
        r = influxdb_conn.query(f"""
        SELECT sum("bytes") AS bytes FROM light WHERE ("user" = $email) AND time >= $last_month_start AND time < $month_start GROUP BY time(1d)
        """, bind_params={'email': self.email, 'last_month_start': last_month_start, 'month_start': month_start}).get_points()
        traffic = [(item['time'], item['bytes']) for item in r if item['bytes'] is not None]
        return traffic


    def month_traffic_by_day(self):
        month_start, next_month_start = get_month_timestamps()
        r = influxdb_conn.query(f"""
        SELECT sum("bytes") AS bytes FROM light WHERE ("user" = $email) AND time >= $month_start AND time < $next_month_start GROUP BY time(1d)
        """, bind_params={'email': self.email, 'month_start': month_start, 'next_month_start': next_month_start}).get_points()
        traffic = [(item['time'], item['bytes']) for item in r if item['bytes'] is not None]
        return traffic
