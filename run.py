#!/usr/bin/env python3
# encoding: utf-8

from app import app
from app import db

if __name__ == '__main__':
    db.create_all()
    app.run(host='127.0.0.1',port=5000)

