#!/usr/bin/env python3
# encoding: utf-8

from app import app
from app import db

if __name__ == '__main__':
    db.create_all()
    app.run(host='0.0.0.0', port=5000, threaded=True)
