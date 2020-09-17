#!/usr/bin/env python3
# encoding: utf-8

import MySQLdb

db = MySQLdb.connect(host=input('host:'),
                     user=input('user:'),
                     passwd=input('password:'),
                     db=input('db:'))

db.autocommit(True)

cur = db.cursor()

cur.execute("""
    CREATE OR REPLACE VIEW radius.lastmonthtraffic AS
        select
            radius.radacct.username AS UserName,
            (sum((radius.radacct.acctinputoctets + radius.radacct.acctoutputoctets))) AS TrafficSum
        from
            radius.radacct
        where
            ((month(radius.radacct.acctstarttime) = month(date_sub(now(),interval 1 month))) and
            (year(radius.radacct.acctstarttime) = year(date_sub(now(),interval 1 month))))
        group by
            radius.radacct.username;
    """)
cur.execute("""
        CREATE OR REPLACE VIEW radius.monthtraffic AS
        select
            radius.radacct.username AS UserName,
            (sum((radius.radacct.acctinputoctets + radius.radacct.acctoutputoctets))) AS TrafficSum
        from
            radius.radacct
        where
            ((month(radius.radacct.acctstarttime) = month(now())) and
            (year(radius.radacct.acctstarttime) = year(now())))
        group by
            radius.radacct.username;
        """)

db.close()
