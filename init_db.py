# -*- coding: utf-8 -*-
"""
Created on Fri Sep 16 15:58:28 2022

@author: Hanniel Shih
"""

import sqlite3

conn = sqlite3.connect('database.db')

with open('schema.sql') as f:
    conn.executescript(f.read())

cur = conn.cursor()

cur.execute("INSERT INTO users (username, password, email) VALUES (?,?,?)",
            ('User1', 'pw', 'em')
            )

conn.commit()
conn.close()
