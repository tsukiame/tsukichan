from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, abort
import sqlite3
import os
import yaml
from time import time
import secrets
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# TODO: Move configuration functions, database functions, etc... to their own files for more organization.

def load_config():
    try:
        with open('config.yml', 'r') as file:
            return yaml.safe_load(file)

    except FileNotFoundError:
        print("Your config.yml file is missing.")
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
                name TEXT,
                option TEXT,
                message TEXT,
                file_path TEXT,
                post_time TEXT,
                parent_post_id INTEGER,
                FOREIGN KEY (board_id) REFERENCES boards(id),
                FOREIGN KEY (parent_post_id) REFERENCES posts(id)
            );
        ''')


        # Insert default boards
        cursor.execute("INSERT INTO boards (name) VALUES ('/devel/'), ('/b/')")

        conn.commit()
        conn.close()
        
        print("Database created successfully.")

    else:
        print(f"Database file '{db_path}' already exists.")

@app.route('/new', methods=['POST'])
def new_post():
    # TODO: Cleanup on thread creation. Delete images and threads which are older than 100.
    name = request.form.get('name')
    option = request.form.get('option')
    message = request.form.get('message')
    board_id = request.form.get('board_id')
    reply_to = request.form.get('reply_to')
    file = request.files['file']

    timestamp = int(time() * 1000)
    filename = ""

    if name == None or name == "":
        name = "Anonymous"

    # TODO: Better handling of filename / getting file type.
    # Splitting can lead to issues without proper input handling. (image.jpg.png for example, or malicious actors)
    # but, this works for a hacky workaround until more critical features are finished.
    if file:
        filename = f"{timestamp}.{secure_filename(file.filename.split('.')[-1])}"
        file.save(os.path.join(load_config()['database']['uploads'], filename))
    else:
        print("No file provided, need to handle this better in the future.")
        abort(403)

    conn = sqlite3.connect(load_config()['database']['path'])
    cursor = conn.cursor()

    if reply_to != None and reply_to != "":
        cursor.execute('''
            INSERT INTO posts (board_id, name, option, message, file_path, post_time, parent_post_id)
            VALUES (?, ?, ?, ?, ?, datetime('now'), ?);
        ''', (board_id, name, option, message, filename, reply_to))
    else:
        cursor.execute('''
            INSERT INTO posts (board_id, name, option, message, file_path, post_time)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        ''', (board_id, name, option, message, filename))

    conn.commit()
    conn.close()

    session['referrer'] = request.referrer
    return redirect(session.pop('referrer', url_for('new_post')))


def get_boards():
    conn = sqlite3.connect(load_config()['database']['path'])
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM boards")
    boards = cursor.fetchall()
    conn.close()

    return boards

def get_board(board_name):
    board_name = f"/{board_name}/"

    conn = sqlite3.connect(load_config()['database']['path'])
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM boards WHERE name=?", (board_name,))
    board = cursor.fetchone()
    conn.close()

    return board

def get_board_posts(board_name):
    board_name = f"/{board_name}/"

    conn = sqlite3.connect(load_config()['database']['path'])
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM posts WHERE
            board_id = (SELECT id FROM boards WHERE name = ?) AND
            parent_post_id IS NULL
        ORDER BY post_time DESC
        LIMIT 100;
        ''', (board_name,))

    posts = cursor.fetchall()
    conn.close()
    print(posts)

    return posts

def get_post(post_id):
    conn = sqlite3.connect(load_config()['database']['path'])
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM posts WHERE id=?", (post_id,))
    post = cursor.fetchone()
    conn.close()

    return post

def get_replies(post_id):
    conn = sqlite3.connect(load_config()['database']['path'])
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM posts WHERE
            parent_post_id=?
    ''', (post_id,))
    replies = cursor.fetchall()
    conn.close()

    return replies    

@app.route('/board/<board_name>/')
def get_root(board_name):
    return render_template('board.html',
        config=load_config(),
        boards=get_boards(),
        current=get_board(board_name),
        posts=get_board_posts(board_name))

@app.route('/board/<board_name>/thread/<post_id>')
def get_thread(board_name, post_id):
    return render_template('thread.html',
        config=load_config(),
        boards=get_boards(),
        current=get_board(board_name),
        op=get_post(post_id),
        replies=get_replies(post_id))

def is_allowed_filename(filename):
    allowed_characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789."
    return all(char in allowed_characters for char in filename)

@app.route('/image/<path:image_name>')
def get_image(image_name):
    image_directory = load_config()['database']['uploads']

    if not is_allowed_filename(image_name):
        abort(403)

    return send_from_directory(image_directory, image_name)

if __name__ == '__main__':
    create_database()
    app.run(debug=True)