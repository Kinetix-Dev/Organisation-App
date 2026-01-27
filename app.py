from flask import Flask, render_template, request, redirect
import sqlite3
import os
import sys

app = Flask(__name__)

@app.route('/')
def signup():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True, port=5555)