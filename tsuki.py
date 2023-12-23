import os
import yaml
import sqlite3
from flask import Flask, render_template

app = Flask(__name__)

def load_config():
    try:
        with open('config.yml', 'r') as file:
            return yaml.safe_load(file)

    except FileNotFoundError:
        print("Your config.json file is missing, please pull from the repository again.")
        return exit(1)

def create_database():
    db_path = load_config()['database']['path']
    if not os.path.exists(db_path):
        print(f"Database file '{db_path}' not found. Creating a new database.")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS boards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                board_id INTEGER,
                image_path TEXT,
                post_time TEXT,
                message TEXT,
                FOREIGN KEY (board_id) REFERENCES boards(id)
            )
        ''')

        # Insert default boards
        cursor.execute("INSERT INTO boards (name) VALUES ('/devel/'), ('/b/')")

        conn.commit()
        conn.close()
        
        print("Database created successfully.")

    else:
        print(f"Database file '{db_path}' already exists.")

def get_boards():
    conn = sqlite3.connect(load_config()['database']['path'])
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM boards")
    boards = cursor.fetchall()
    conn.close()

    return boards

@app.route('/')
def get_root():
    return render_template('index.html',
        config=load_config(),
        boards=get_boards())

if __name__ == '__main__':
    create_database()
    app.run(debug=True)