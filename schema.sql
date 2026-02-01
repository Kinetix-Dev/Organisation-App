CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    total_points INTEGER DEFAULT 0
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL
    title TEXT NOT NULL
    task_type TEXT,
    difficulty TEXT,
    points_value INTEGER,
    is recurring BOOLEAN DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users (id)
)