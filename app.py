from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = "секретный_ключ_123"  # нужен для сессий
DB = "messages.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    today = datetime.now().strftime("%d.%m.%Y")
    return render_template('index.html', name="Имухамед", date=today)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        message = request.form['message']
        conn = get_db()
        conn.execute("INSERT INTO messages (name, message) VALUES (?, ?)", (name, message))
        conn.commit()
        conn.close()
        return redirect(url_for('messages'))
    return render_template('contact.html')

@app.route('/messages')
def messages():
    conn = get_db()
    rows = conn.execute("SELECT * FROM messages ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('messages.html', messages=rows)

@app.route('/delete/<int:msg_id>')
def delete_message(msg_id):
    conn = get_db()
    conn.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('messages'))

# ========== РЕГИСТРАЦИЯ ==========
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Хешируем пароль
        password_hash = generate_password_hash(password)

        conn = get_db()
        try:
            conn.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                         (username, email, password_hash))
            conn.commit()
            conn.close()
            flash("Регистрация успешна! Теперь войдите.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            flash("Пользователь с таким именем или email уже существует.", "error")
            return redirect(url_for('register'))

    return render_template('register.html')

# ========== ВХОД ==========
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash("Вы успешно вошли!", "success")
            return redirect(url_for('profile'))
        else:
            flash("Неверное имя или пароль.", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

# ========== ЛИЧНЫЙ КАБИНЕТ ==========
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash("Сначала войдите в систему.", "error")
        return redirect(url_for('login'))
    return render_template('profile.html', username=session['username'])

# ========== ВЫХОД ==========
@app.route('/logout')
def logout():
    session.clear()
    flash("Вы вышли из системы.", "success")
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)