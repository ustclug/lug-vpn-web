import datetime
import random
import string
import xml.etree.ElementTree as ET

import requests


EXPIRATION_TYPES = ('semester', 'year', 'long')


class LibraryAPIError(Exception):
    pass


def random_string(length):
    alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return ''.join(random.choice(alphabet) for _ in range(length))


def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return '%3.2f %s%s' % (num, unit, suffix)
        num /= 1024.0
    return '%.2f %s%s' % (num, 'Yi', suffix)


def expiration_date(expiration_type, today=None):
    today = today or datetime.date.today()
    if expiration_type not in EXPIRATION_TYPES:
        raise ValueError('Unknown expiration type: {}'.format(expiration_type))

    if today.month < 3:
        semester = datetime.date(today.year, 9, 1)
    elif today.month < 9:
        semester = datetime.date(today.year + 1, 3, 1)
    else:
        semester = datetime.date(today.year + 1, 9, 1)

    if expiration_type == 'semester':
        return semester
    if expiration_type == 'long':
        return semester.replace(year=semester.year + 3)
    if today.month < 3:
        return datetime.date(today.year, 9, 20)
    return datetime.date(today.year + 1, 9, 20)


def next_semester_end(extra_years=0):
    result = expiration_date('semester')
    return result.replace(year=result.year + extra_years)


def next_school_year_end():
    return expiration_date('year')


def fetch_from_lib_api(endpoint, studentno, timeout=5):
    try:
        response = requests.get(endpoint, params={'id': studentno}, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise LibraryAPIError('Library API request failed') from exc

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError as exc:
        raise LibraryAPIError('Library API returned malformed XML') from exc
    if root.tag != 'reader_info':
        raise LibraryAPIError('Library API returned an unexpected response')
    return {child.tag: child.text for child in root}
