#!/usr/bin/env python3
# encoding: utf-8

from app import app
from app import db

if __name__ == '__main__':
    db.create_all()
    db.engine.execute("""
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
            radius.radacct.username
        order by
            (sum((radius.radacct.acctinputoctets + radius.radacct.acctoutputoctets)));
    """)
    db.engine.execute("""
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
            radius.radacct.username
        order by
            (sum((radius.radacct.acctinputoctets + radius.radacct.acctoutputoctets)));
        """)
    app.run(host='0.0.0.0', port=5000, threaded=True)

