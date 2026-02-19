from flask import Flask, render_template, request, redirect, flash, url_for, session
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import os.path
import sys

currentdirectory = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(currentdirectory, 'database.db')

app = Flask(__name__)
app.secret_key = 'this-key-is-very-secret'

@app.route('/')
def redirect_signup():
    return redirect(url_for('register'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['Email']
        password = request.form['Password']
        hashed_pass = generate_password_hash(password)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid Email or Password')
            return render_template('login.html', page='login')

    return render_template('login.html', page='login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['Email']
        password = request.form['Password']

        hashed_pass = generate_password_hash(password)

        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO users (email, password_hash) VALUES (?, ?)', (email, hashed_pass))
                conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already registered!')
            return render_template('login.html', page='register')

    return render_template('login.html', page='register')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Please log in first!")
        return redirect(url_for('login'))

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    user = cursor.execute('SELECT * from users WHERE id = ?', (session['user_id'],)).fetchone()
    points_query = 'SELECT SUM(points_value) FROM tasks WHERE user_id = ? AND is_completed = 1'
    total_points = cursor.execute(points_query, (session['user_id'],)).fetchone()[0] or 0
    tasks = cursor.execute('SELECT * from tasks WHERE user_id = ? AND is_completed = 0', (session['user_id'],)).fetchall()
    conn.close()

    return render_template('dashboard.html', user=user, tasks=tasks, points=total_points)
    
@app.route('/add_task', methods=['POST'])
def add_task():
    if 'user_id' not in session:
        flash("Please log in first!")
        return redirect(url_for('login'))

    title = request.form.get('title')
    difficulty = request.form.get('difficulty')
    points_map = {"Easy" : 10, "Medium" : 20, "Hard" : 50}
    points_value = points_map.get(difficulty, 10)
    task_type = request.form.get('task_type')
    due_date = request.form.get('due_date')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO tasks (user_id, title, difficulty, task_type, due_date, points_value) VALUES (?, ?, ?, ?, ?, ?)', (session['user_id'], title, difficulty, task_type, due_date, points_value))
    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))

@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    if 'user_id' not in session:
        flash("Please log in first!")
        return redirect(url_for('login'))
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', (task_id, session['user_id']))
    flash("Task deleted!")
    return redirect(url_for('dashboard'))

@app.route('/edit_task/<int:task_id>', methods=['POST'])
def edit_task(task_id):
    if 'user_id' not in session:
        flash("Please log in first!")
        return redirect(url_for('login'))
    
    title = request.form.get('title')
    difficulty = request.form.get('difficulty')
    points_value = request.form.get('points_value')
    due_date = request.form.get('due_date')
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''UPDATE tasks 
                       SET title = ?, difficulty = ?, points_value = ?, due_date = ?
                       WHERE id = ? AND user_id = ?''', (title, difficulty, points_value, due_date, task_id, session['user_id']))
        flash("Task updated!")
        return redirect(url_for('dashboard'))

@app.route('/complete_task/<int:task_id>')
def complete_task(task_id):
   if 'user_id' not in session:
        flash("Please log in first!")
        return redirect(url_for('login'))
   
   with sqlite3.connect(db_path) as conn:
       cursor = conn.cursor()
       cursor.execute('UPDATE tasks SET is_completed = 1 WHERE id = ? AND user_id = ?', (task_id, session['user_id']))

       flash("Task completed! Points awarded.")
       return redirect(url_for('dashboard'))
    

if __name__ == '__main__':
    app.run(debug=True, port=5555)