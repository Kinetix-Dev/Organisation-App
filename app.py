from flask import Flask, render_template, request, redirect, flash, url_for, session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
import sqlite3
import os.path
import sys
from flask_mail import Mail, Message
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

currentdirectory = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(currentdirectory, 'database.db')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

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

    today_index = str(datetime.now().weekday())
    user_id = session['user_id']
    active_filter = request.args.get('filter')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE tasks
        SET is_completed = 0
        WHERE is_recurring = 1 
        AND is_completed = 1 
        AND recurring_days LIKE ?
''', (f'%{today_index}%',))
    conn.commit()

    user = cursor.execute('SELECT * from users WHERE id = ?', (session['user_id'],)).fetchone()
    points_query = 'SELECT SUM(points_value) FROM tasks WHERE user_id = ? AND is_completed = 1'
    total_points = cursor.execute(points_query, (session['user_id'],)).fetchone()[0] or 0
    query = 'SELECT * FROM tasks WHERE user_id  = ? AND is_completed = 0'
    params = [user_id]
    if active_filter:
        query += ' AND task_type = ?'
        params.append(active_filter)

    tasks = cursor.execute(query, params).fetchall()

    calendar_events = []
    for task in tasks:
        if task['is_recurring'] and task['recurring_days']:
            days_to_repeat = [int(d) for d in task['recurring_days'].split(',')]
            start_date = datetime.now()
            for i in range(30):
                current_date = start_date + timedelta(days=i)
                if current_date.weekday() in days_to_repeat:
                    calendar_events.append({
                        'title': f"🔁 {task['title']}",
                        'start': current_date.strftime('%Y-%m-%d'),
                        'color': '#198754' if task['task_type'] == 'Fitness' else ('#6c757d' if task['task_type'] == 'Personal' else '#0d6efd')
                    })
        else:
            calendar_events.append({
                'title': task['title'],
                'start': task['due_date'],
                'color': '#198754' if task['task_type'] == 'Fitness' else ('#6c757d' if task['task_type'] == 'Personal' else '#0d6efd')
            })
    conn.close()

    return render_template('dashboard.html', user=user, tasks=tasks, points=total_points, active_filter=active_filter, events=calendar_events)
    
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
    is_recurring = 1 if request.form.get('is_recurring') else 0
    selected_days = request.form.getlist('days')
    recurring_days = ",".join(selected_days) if is_recurring else ""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO tasks (user_id, title, difficulty, task_type, due_date, points_value, is_recurring, recurring_days) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (session['user_id'], title, difficulty, task_type, due_date, points_value, is_recurring, recurring_days))
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
    is_recurring = 1 if request.form.get('is_recurring') else 0
    selected_days = request.form.getlist('days')
    recurring_days = ",".join(selected_days) if is_recurring else ""
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''UPDATE tasks 
                       SET title = ?, difficulty = ?, points_value = ?, due_date = ?, is_recurring = ?, recurring_days = ?
                       WHERE id = ? AND user_id = ?''', (title, difficulty, points_value, due_date, is_recurring, recurring_days, task_id, session['user_id']))
        flash("Task updated!")
        conn.commit()
        return redirect(url_for('dashboard'))

@app.route('/complete_task/<int:task_id>')
def complete_task(task_id):
   if 'user_id' not in session:
        flash("Please log in first!")
        return redirect(url_for('login'))
   
   with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        task = cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()

        if task['is_recurring']:
            next_date = (datetime.strptime(task['due_date'], '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
            cursor.execute('UPDATE tasks SET due_date = ? WHERE id = ? AND user_id = ?', (next_date, task_id, session['user_id']))
        else:
            cursor.execute('UPDATE tasks SET is_completed = 1 WHERE id = ? AND user_id = ?', (task_id, session['user_id']))

        flash("Task completed! Points awarded.")
        return redirect(url_for('dashboard'))
    
@app.route('/leaderboard')
def leaderboard():
    with sqlite3.connect(db_path) as conn:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        points_query = 'SELECT SUM(points_value) FROM tasks WHERE user_id = ? AND is_completed = 1'
        total_points = cursor.execute(points_query, (session['user_id'],)).fetchone()[0] or 0
        query = '''
            SELECT users.email,
            SUM(tasks.points_value) as total_earned
            FROM users
            JOIN tasks ON users.id = tasks.user_id
            WHERE tasks.is_completed = 1
            GROUP BY users.id
            ORDER BY total_points DESC
        '''
        users_ranking = cursor.execute(query).fetchall()
        return render_template('leaderboard.html', rankings=users_ranking, points=total_points)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash("Please log in first!")
        return redirect(url_for('login'))
    
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        user = cursor.execute('SELECT email FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        points_query = 'SELECT SUM(points_value) FROM tasks WHERE user_id = ? AND is_completed = 1'
        total_points = cursor.execute(points_query, (session['user_id'],)).fetchone()[0] or 0
        task_count = cursor.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ?', (session['user_id'],)).fetchone()[0]
    return render_template('profile.html', user=user, points=total_points, task_count=task_count)

app.config['MAIL_SERVER'] = 'sandbox.smtp.mailtrap.io'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
    print("WARNING Mail credentials not found. Check your .env file!")

def send_reminder(user_email, task_title, task_points):
    with app.app_context():
        msg = Message(
            subject=f"Don't miss out on {task_points} points!",
            sender="noreply@placid-app.com",
            recipients=[user_email]
        )
        msg.body = f"Your task '{task_title}' is waiting for you. Complete it now to boost your score!"

        try:
            mail.send(msg)
            print("Email sent successfully to Mailtrap!")
        except Exception as e:
            print(f"Error sending email as {e}")

def schedule_reminders():
    with app.app_context():
        now = datetime.now()
        tomorrow = (now + timedelta(days=1)).strftime('%Y-%m-%d')

        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = '''
                SELECT users.email, tasks.title, tasks.points_value
                FROM tasks
                JOIN users ON tasks.user_id = users.id
                WHERE tasks.due_date = ? AND tasks.is_completed = 0
'''
            due_tasks = cursor.execute(query, (tomorrow,)).fetchall()

            for task in due_tasks:
                send_reminder(task['email'], task['title'], task['points_value'])

mail = Mail(app)

scheduler = BackgroundScheduler()
scheduler.add_job(func=schedule_reminders, trigger="interval", hours=24)
scheduler.start()

if __name__ == '__main__':
    app.run(debug=True, port=5555, use_reloader=False)