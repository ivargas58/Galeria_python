from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
import bcrypt

app = Flask(__name__)
app.secret_key = 'secret_key'

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Crear la base de datos y las tablas
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Tabla de usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # Tabla de obras de arte
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS artworks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            image TEXT NOT NULL,
            description TEXT NOT NULL,
            creation_date TEXT NOT NULL
        )
    ''')
    
    password = os.getenv('ADMIN_PASSWORD')
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Guardar la contraseña encriptada en la base de datos
    cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", 
               ('admin', hashed_password, 'admin'))

    cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('cliente', 'cliente123', 'cliente')")

    conn.commit()
    conn.close()

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def home():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Recuperar todas las obras de la base de datos
    cursor.execute('SELECT * FROM artworks')
    artworks = cursor.fetchall()
    conn.close()

    return render_template('home.html', artworks=artworks)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['username'] = user[1]
            session['role'] = user[3]
            if user[3] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return "Bienvenido, cliente"
        else:
            return "Usuario o contraseña incorrectos"
    return render_template('login.html')

@app.route('/admin-dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'username' in session and session['role'] == 'admin':
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        if request.method == 'POST':
            # Agregar obra de arte
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
    else:
        return redirect(url_for('login'))

@app.route('/edit/<int:artwork_id>', methods=['GET', 'POST'])
def edit_artwork(artwork_id):
    if 'username' in session and session['role'] == 'admin':
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            creation_date = request.form['creation_date']
            image = request.files.get('image')

            if image and image.filename:
                filename = secure_filename(image.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(filepath)
                cursor.execute('''
                    UPDATE artworks
                    SET title = ?, image = ?, description = ?, creation_date = ?
                    WHERE id = ?
                ''', (title, filename, description, creation_date, artwork_id))
            else:
                cursor.execute('''
                    UPDATE artworks
                    SET title = ?, description = ?, creation_date = ?
                    WHERE id = ?
                ''', (title, description, creation_date, artwork_id))

            conn.commit()
            conn.close()
            flash('Obra de arte actualizada exitosamente.')
            return redirect(url_for('admin_dashboard'))

        cursor.execute('SELECT * FROM artworks WHERE id = ?', (artwork_id,))
        artwork = cursor.fetchone()
        conn.close()
        return render_template('edit_artwork.html', artwork=artwork)

    return redirect(url_for('login'))

@app.route('/delete/<int:artwork_id>', methods=['POST'])
def delete_artwork(artwork_id):
    if 'username' in session and session['role'] == 'admin':
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # Eliminar la obra de la base de datos
        cursor.execute('DELETE FROM artworks WHERE id = ?', (artwork_id,))
        conn.commit()
        conn.close()

        flash('Obra de arte eliminada exitosamente.')
        return redirect(url_for('admin_dashboard'))

    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))
