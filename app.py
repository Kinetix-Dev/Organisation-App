from flask import Flask, render_template, request, redirect
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import os
import sys

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def redirect_signup():
    return redirect('/register')

@app.route('/register')
def register():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True, port=5555)