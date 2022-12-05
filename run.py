#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep 16 15:42:54 2022

@author: Hanniel Shih
"""

import sqlite3
from flask import Flask, request, g, render_template, url_for, flash, redirect, session, Markup
import os
import pandas as pd
import pickle
app = Flask(__name__)







DATABASE = 'database.db'

app.config.from_object(__name__)
app.config['SECRET_KEY'] = 'qwerty'
app.config['UPLOAD_FOLDER'] = 'files/'
app.config['IMAGE_FOLDER'] = os.path.join('static', 'image')

with open(os.path.join('static','data','display.pkl'), 'rb') as f:
    df_display = pickle.load(f)
hh_nums = list(df_display['HSHD_NUM'].unique())

def connect_to_database():
    return sqlite3.connect(app.config['DATABASE'])

def get_db():
    db = getattr(g, 'db', None)
    if db is None:
        db = g.db = connect_to_database()
    return db

def get_user_status(s):
    username = s.get('username', None)
    return 'You are not logged in' if username is None else f'Hello {username}'

@app.route('/login/', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not (username and password):
            flash('Please fill in every field')
        else:
            rows = execute_query("""SELECT * FROM users WHERE username=? AND password=?""", (username, password))
            if len(rows) == 0:
                flash('User does not exist or wrong password')
            else:
                session['username'] = username
                return redirect(url_for('index'))
    user_status = get_user_status(session)
    return render_template('login.html', user_status=user_status)

@app.route('/register/', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        if not (username and password and email):
            flash('Please fill in every field')
        elif execute_query("""SELECT * FROM users WHERE username=?""", (username,)) != []:
            flash('Username already existed, please choose a different one')
        else:
            execute_post("INSERT INTO users (username, password, email) VALUES (?,?,?)",
                        (username, password, email))
            session['username'] = username
            flash('Sign up sucessful, please log in')
            return redirect(url_for('login'))
    user_status = get_user_status(session)
    return render_template('register.html', user_status=user_status)

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()
        
def execute_post(post, args=()):
    conn = get_db()
    conn.execute(post, args)
    conn.commit()
    conn.close()
    
def execute_query(query, args=()):
    cur = get_db().execute(query, args)
    rows = cur.fetchall()
    cur.close()
    return rows

def get_HSHD(df, num):
    return df[df['HSHD_NUM']==num].copy()

@app.route('/', methods=("POST", "GET"))
def index():
    image1 = os.path.join(app.config['IMAGE_FOLDER'], '1.png')
    image2 = os.path.join(app.config['IMAGE_FOLDER'], '2.png')
    image3 = os.path.join(app.config['IMAGE_FOLDER'], '3.png')
    user_status = get_user_status(session)
    return render_template("index.html", image1=image1, image2=image2, image3=image3, user_status=user_status)

@app.route('/H10')
def H10():
    full_filename = os.path.join(app.config['IMAGE_FOLDER'], 'chase.jpg')
    user_status = get_user_status(session)
    return render_template('h10.html', tables=[get_HSHD(df_display, 10).to_html(classes='data', header='true', index=False)], user_image=full_filename, user_status=user_status)

@app.route('/choice', methods=('GET', 'POST'))
def choice():
    if request.method == 'POST':
        hh_num = request.form['hh_num']

        try:
            hh_num = int(hh_num)
        except ValueError:
            flash('Please input a number')
        else:
            if not (int(hh_num) in hh_nums):
                flash('This household number does not exist')
            else:
                session['hh_num'] = hh_num
                session['custom'] = 0
                return redirect(url_for('view_h'))
    user_status = get_user_status(session)
    return render_template('choice.html', user_status=user_status)

@app.route('/view_h')
def view_h():
    hh_num = int(session['hh_num'])
    custom = int(session['custom'])
    if custom == 0:
        df = get_HSHD(df_display, hh_num)
    elif custom == 1:
        global df_custom
        if df_custom is None:
            df_custom = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'display.csv'))
        df = get_HSHD(df_custom, hh_num)
    user_status = get_user_status(session)
    return render_template('view_h.html', tables=[df.to_html(classes='data', header='true', index=False)], hh_num=hh_num, user_status=user_status)

@app.route('/upload', methods=('GET', 'POST'))
def upload():
    if request.method == 'POST':
        file_h = request.files['file_h']
        file_t = request.files['file_t']
        file_p = request.files['file_p']
        
        file_h.save(os.path.join(app.config['UPLOAD_FOLDER'], 'h.csv'))
        file_t.save(os.path.join(app.config['UPLOAD_FOLDER'], 't.csv'))
        file_p.save(os.path.join(app.config['UPLOAD_FOLDER'], 'p.csv'))
        print('files saved')
        try:
            global df_custom, hh_nums_custom
            df_custom = read(os.path.join(app.config['UPLOAD_FOLDER'], 'h.csv'), os.path.join(app.config['UPLOAD_FOLDER'], 't.csv'), os.path.join(app.config['UPLOAD_FOLDER'], 'p.csv'))
            df_custom.to_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'display.csv'))
            hh_nums_custom = list(df_custom['HSHD_NUM'].unique())
        except Exception as e:
            flash(Markup(f'Error processing file, please check file format.<br/>Error: {e}'))
            print(e)
        else:
            flash('Files processing completed!')
    user_status = get_user_status(session)
    return render_template('upload.html', user_status=user_status)

@app.route('/choice_custom', methods=('GET', 'POST'))
def choice_custom():
    if not os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], 'display.csv')):
        return render_template('processing.html')
    else:
        if request.method == 'POST':
            global df_custom, hh_nums_custom
            hh_num = request.form['hh_num']
            
            if df_custom is None:
                df_custom = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'display.csv'))
            if hh_nums_custom is None:
                hh_nums_custom = list(df_custom['HSHD_NUM'].unique())

            try:
                hh_num = int(hh_num)
            except ValueError:
                flash('Please input a number')
            else:
                if not (int(hh_num) in hh_nums_custom):
                    flash('This household number does not exist')
                else:
                    session['hh_num'] = hh_num
                    session['custom'] = 1
                    return redirect(url_for('view_h'))
        user_status = get_user_status(session)
        return render_template('choice_custom.html', user_status=user_status)

def get_date(df, year='YEAR', week='WEEK_NUM'):
    df = df.copy()
    df['formatted_date'] = df[year] * 1000 + df[week] * 10 + 4
    df['date'] = pd.to_datetime(df['formatted_date'], format='%Y%W%w')
    return df['date'].copy()

def read(dir_h, dir_t, dir_p):
    df_h = pd.read_csv(dir_h)
    df_t = pd.read_csv(dir_t)
    df_p = pd.read_csv(dir_p)

    df_h.columns = [c.replace(' ', '') for c in df_h.columns]
    df_t.columns = [c.replace(' ', '') for c in df_t.columns]
    df_p.columns = [c.replace(' ', '') for c in df_p.columns]
    
    df_all = df_h.merge(df_t, on='HSHD_NUM', how='left').merge(df_p, on='PRODUCT_NUM', how='left')

    df_all['DATE'] = get_date(df_all)
    df_all = df_all.sort_values(['HSHD_NUM', 'BASKET_NUM', 'DATE', 'PRODUCT_NUM', 'DEPARTMENT', 'COMMODITY'], axis=0)
    df_display = df_all[['HSHD_NUM', 'BASKET_NUM', 'DATE', 'PRODUCT_NUM', 'DEPARTMENT', 'COMMODITY', 'SPEND', 'UNITS', 'STORE_R', 'WEEK_NUM', 'YEAR', 'L', 'AGE_RANGE', 'MARITAL', 'INCOME_RANGE', 'HOMEOWNER', 'HSHD_COMPOSITION', 'HH_SIZE', 'CHILDREN', 'PURCHASE_', 'BRAND_TY', 'NATURAL_ORGANIC_FLAG']]
    # df_display = df_display.set_index('HSHD_NUM')
    
    return df_display.copy()

if __name__ == '__main__':
  app.run()
  
  
  
  
