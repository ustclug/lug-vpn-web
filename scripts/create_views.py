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
            radius.radacct.acctstarttime >= DATE_FORMAT(NOW() - INTERVAL 1 MONTH, '%Y-%m-01')
            AND radius.radacct.acctstarttime < DATE_FORMAT(NOW(), '%Y-%m-01')
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
            radius.radacct.acctstarttime >= DATE_FORMAT(NOW(), '%Y-%m-01')
            AND radius.radacct.acctstarttime < DATE_FORMAT(NOW() + INTERVAL 1 MONTH, '%Y-%m-01')
        group by
            radius.radacct.username;
        """)

db.close()
