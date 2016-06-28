#!/usr/bin/env python3
# encoding: utf-8

import MySQLdb
import random
import hashlib
import string

db = MySQLdb.connect(host=input('host:'),
                     user=input('user:'),
                     passwd=input('password:'),
                     db=input('db:'))

db.autocommit(True)

cur = db.cursor()

cur.execute("rename table `user` to `user_bak`")

cur.execute("""
CREATE TABLE `user` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `email` varchar(63) DEFAULT NULL,
  `passwordhash` varchar(127) NOT NULL,
  `salt` varchar(127) NOT NULL,
  `active` tinyint(1) DEFAULT NULL,
  `admin` tinyint(1) DEFAULT NULL,
  `status` enum('none','applying','pass','reject','banned') DEFAULT NULL,
  `name` varchar(127) DEFAULT NULL,
  `studentno` varchar(127) DEFAULT NULL,
  `phone` varchar(127) DEFAULT NULL,
  `reason` text,
  `applytime` datetime DEFAULT NULL,
  `vpnpassword` varchar(127) DEFAULT NULL,
  `rejectreason` text,
  `banreason` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) CHARSET=utf8
""")

cur.execute("""
insert into user
(`id`,`email`,`active`,`admin`,`status`,`name`,`studentno`,`phone`,`reason`,`applytime`,`vpnpassword`,`passwordhash`,`salt`)
select `id`,`email`,`active`,`admin`,`apply`,`name`,`studentno`,`phone`,`reason`,`applytime`,
(select `value` from `radcheck` where username=user_bak.email),'',''
from user_bak
where 1
""")

cur.execute('select id,password from user_bak')

for row in cur.fetchall():
    id = row[0]
    p = row[1]
    salt = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for i in range(10))
    s = hashlib.sha256()
    s.update(p.encode('utf-8'))
    s.update(salt.encode('utf-8'))
    passwordhash = s.hexdigest()
    cur.execute('update user set passwordhash=%s,salt=%s where id=%s', (passwordhash, salt, id))

db.close()
