import random
import string
import datetime


def random_string(N):
    return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for i in range(N))


def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.2f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.2f %s%s" % (num, 'Yi', suffix)


def next_semester_end(extra_years=0):
    today = datetime.date.today()
    if today.month < 3:
        return datetime.date(today.year + extra_years, 9, 1) + datetime.timedelta(days=-1)
    elif today.month < 9:
        return datetime.date(today.year + extra_years + 1, 3, 1) + datetime.timedelta(days=-1)
    else:
        return datetime.date(today.year + extra_years + 1, 9, 1) + datetime.timedelta(days=-1)
