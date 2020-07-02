import random
import string
import datetime
import requests
import xml.etree.ElementTree as ET


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


def next_school_year_end():
    today = datetime.date.today()
    if today.month < 3:
        return datetime.date(today.year, 9, 20)
    else:
        return datetime.date(today.year + 1, 9, 20)


def this_school_year_end():
    return next_school_year_end() - datetime.timedelta(365)  # Ignore leap years


def fetch_from_lib_api(studentno):
    params = {"id": studentno}
    url = "http://api.lib.ustc.edu.cn:9380/get_info_from_id.php"
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return {'message': "query failed"}
    root = ET.fromstring(response.text)
    if root.tag != "reader_info":
        return {'message': "bad XML response"}
    return {key.tag: key.text for key in root}
