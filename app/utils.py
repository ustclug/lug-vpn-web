import random
import string
import datetime
import hashlib
from base64 import b64encode

def hash_passwd_with_salt(passwd, salt):
    ctx = hashlib.sha256(passwd)
    ctx.update(salt)
    #hash = b"{SSHA256}" + b64encode(ctx.digest() + salt)
    hash_clean = b64encode(ctx.digest() + salt)
    return hash_clean

def hash_passwd(passwd):
    salt = random_string(8).encode('utf-8')
    return hash_passwd_with_salt(passwd,salt)

def random_string(N):
    return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for i in range(N))


def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.2f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.2f %s%s" % (num, 'Yi', suffix)


def next_semester_end():
    today = datetime.date.today()
    if today.month < 3:
        return datetime.date(today.year, 9, 1) + datetime.timedelta(days=-1)
    elif today.month < 9:
        return datetime.date(today.year + 1, 3, 1) + datetime.timedelta(days=-1)
    else:
        return datetime.date(today.year + 1, 9, 1) + datetime.timedelta(days=-1)
