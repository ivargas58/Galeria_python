import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import sqlite3
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import bcrypt

# Cargar las variables de entorno del archivo .env
load_dotenv()

# Crear la aplicación Flask
app = Flask(__name__)

# Clave secreta de la sesión de Flask
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default_secret_key")

# Configurar carpeta de subida
UPLOAD_FOLDER = './uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Ruta de la base de datos
DB_PATH = './database.db'

# Crear la base de datos y las tablas
# Crear la base de datos y las tablas
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Crear tabla de usuarios
    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # Crear tabla de obras de arte
    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS artworks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            image TEXT NOT NULL,
            description TEXT NOT NULL,
            creation_date TEXT NOT NULL
        )
    ''')

    # Crear usuario administrador si no existe
    cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", 
                   ('admin', 'admin123', 'admin'))
    conn.commit()
    conn.close()

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def home():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM artworks')
    artworks = cursor.fetchall()
    conn.close()
    return render_template('home.html', artworks=artworks)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            session['username'] = user[1]
            session['role'] = user[3]
            if user[3] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('home'))
        flash("Usuario o contraseña incorrectos.")
    return render_template('login.html')

@app.route('/admin-dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'username' in session and session['role'] == 'admin':
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            creation_date = request.form['creation_date']
            image = request.files['image']

            if image:
                filename = secure_filename(image.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(filepath)

                cursor.execute(''' 
                    INSERT INTO artworks (title, image, description, creation_date)
                    VALUES (?, ?, ?, ?)
                ''', (title, filename, description, creation_date))
                conn.commit()
                flash('Obra de arte agregada exitosamente.')

        cursor.execute('SELECT * FROM artworks')
        artworks = cursor.fetchall()
        conn.close()
        return render_template('admin_dashboard.html', artworks=artworks)
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))
