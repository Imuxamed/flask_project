from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import secrets
from werkzeug.utils import secure_filename
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

def format_time(timestamp):
    """Превращает '2026-10-05 14:30:00' в '5 минут назад'."""
    try:
        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    except:
        return timestamp

    now = datetime.now()
    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return "только что"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} мин. назад"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} ч. назад"
    elif seconds < 604800:
        days = int(seconds // 86400)
        return f"{days} дн. назад"
    else:
        return dt.strftime("%d.%m.%Y")

app = Flask(__name__)
app.secret_key = "секретный_ключ_123"
UPLOAD_FOLDER = 'static/avatars'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
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

# ========== ГОСТЕВАЯ ==========
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if 'user_id' not in session:
        flash("Сначала войдите, чтобы оставить сообщение.", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':
        message = request.form['message']
        name = session['username']
        conn = get_db()
        conn.execute("INSERT INTO messages (name, message) VALUES (?, ?)", (name, message))
        conn.commit()
        conn.close()
        return redirect(url_for('messages'))
    return render_template('contact.html')

@app.route('/messages')
def messages():
    conn = get_db()
    rows = conn.execute("""
        SELECT messages.id, messages.name, messages.message, messages.created_at,
               users.avatar
        FROM messages
        LEFT JOIN users ON messages.name = users.username
        ORDER BY messages.id DESC
    """).fetchall()
    count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]

    current_user = None
    if 'user_id' in session:
        current_user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()

    formatted = []
    for row in rows:
        comments = conn.execute("""
            SELECT comments.*, users.avatar
            FROM comments
            LEFT JOIN users ON comments.username = users.username
            WHERE comments.message_id = ?
            ORDER BY comments.id ASC
        """, (row['id'],)).fetchall()

        can_delete = False
        if current_user:
            if current_user['is_admin'] == 1 or current_user['username'] == row['name']:
                can_delete = True

        formatted.append({
            'id': row['id'],
            'name': row['name'],
            'message': row['message'],
            'created_at': format_time(row['created_at']),
            'avatar': row['avatar'],
            'can_delete': can_delete,
            'comments': comments
        })

    conn.close()
    return render_template('messages.html', messages=formatted, count=count)

# ========== УДАЛЕНИЕ СООБЩЕНИЯ ==========
@app.route('/delete/<int:msg_id>')
def delete_message(msg_id):
    if 'user_id' not in session:
        flash("Войдите, чтобы удалять сообщения.", "error")
        return redirect(url_for('login'))

    conn = get_db()
    msg = conn.execute("SELECT * FROM messages WHERE id = ?", (msg_id,)).fetchone()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()

    if not msg:
        conn.close()
        flash("Сообщение не найдено.", "error")
        return redirect(url_for('messages'))

    if user['is_admin'] == 1 or msg['name'] == user['username']:
        conn.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
        conn.commit()
        conn.close()
        flash("Сообщение удалено.", "success")
    else:
        conn.close()
        flash("Вы можете удалять только свои сообщения.", "error")

    return redirect(url_for('messages'))

# ========== ДОБАВЛЕНИЕ КОММЕНТАРИЯ ==========
@app.route('/add_comment/<int:msg_id>', methods=['POST'])
def add_comment(msg_id):
    if 'user_id' not in session:
        flash("Войдите, чтобы оставить комментарий.", "error")
        return redirect(url_for('login'))

    text = request.form['text']
    if text.strip():
        conn = get_db()
        conn.execute("INSERT INTO comments (message_id, username, text) VALUES (?, ?, ?)",
                     (msg_id, session['username'], text))
        conn.commit()
        conn.close()
        flash("Комментарий добавлен!", "success")
    return redirect(url_for('messages'))

# ========== РЕГИСТРАЦИЯ ==========
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
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

# ========== ПРОФИЛЬ ==========
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash("Сначала войдите в систему.", "error")
        return redirect(url_for('login'))

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('profile.html', username=session['username'], user=user)

# ========== ВЫХОД ==========
@app.route('/logout')
def logout():
    session.clear()
    flash("Вы вышли из системы.", "success")
    return redirect(url_for('home'))

# ========== РЕДАКТИРОВАНИЕ ПРОФИЛЯ ==========
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        flash("Сначала войдите в систему.", "error")
        return redirect(url_for('login'))

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()

    if request.method == 'POST':
        new_username = request.form['username']
        new_email = request.form['email']

        try:
            conn.execute("UPDATE users SET username = ?, email = ? WHERE id = ?",
                         (new_username, new_email, session['user_id']))
            conn.commit()
            session['username'] = new_username
            flash("Профиль обновлён!", "success")
        except sqlite3.IntegrityError:
            flash("Это имя или email уже заняты.", "error")

        conn.close()
        return redirect(url_for('profile'))

    conn.close()
    return render_template('edit_profile.html', user=user)

# ========== СМЕНА ПАРОЛЯ ==========
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        flash("Сначала войдите в систему.", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':
        old_password = request.form['old_password']
        new_password = request.form['new_password']

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()

        if user and check_password_hash(user['password_hash'], old_password):
            new_hash = generate_password_hash(new_password)
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                         (new_hash, session['user_id']))
            conn.commit()
            conn.close()
            flash("Пароль успешно изменён!", "success")
            return redirect(url_for('profile'))
        else:
            conn.close()
            flash("Старый пароль неверный.", "error")
            return redirect(url_for('change_password'))

    return render_template('change_password.html')

# ========== ЗАБЫЛИ ПАРОЛЬ ==========
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user:
            token = secrets.token_hex(8)
            conn.execute("UPDATE users SET reset_token = ? WHERE id = ?", (token, user['id']))
            conn.commit()
            conn.close()
            flash(f"Ваш токен для сброса: {token}", "success")
            return redirect(url_for('reset_password'))
        else:
            conn.close()
            flash("Пользователь с таким email не найден.", "error")
            return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')

# ========== СБРОС ПАРОЛЯ ==========
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        token = request.form['token']
        new_password = request.form['new_password']

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE reset_token = ?", (token,)).fetchone()

        if user:
            new_hash = generate_password_hash(new_password)
            conn.execute("UPDATE users SET password_hash = ?, reset_token = NULL WHERE id = ?",
                         (new_hash, user['id']))
            conn.commit()
            conn.close()
            flash("Пароль успешно сброшен! Теперь войдите.", "success")
            return redirect(url_for('login'))
        else:
            conn.close()
            flash("Неверный токен.", "error")
            return redirect(url_for('reset_password'))

    return render_template('reset_password.html')

# ========== ЗАГРУЗКА АВАТАРКИ ==========
@app.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    if 'user_id' not in session:
        flash("Сначала войдите в систему.", "error")
        return redirect(url_for('login'))

    file = request.files['avatar']
    if file and file.filename:
        filename = secure_filename(file.filename)
        filename = f"user_{session['user_id']}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        conn = get_db()
        conn.execute("UPDATE users SET avatar = ? WHERE id = ?", (filename, session['user_id']))
        conn.commit()
        conn.close()
        flash("Аватарка загружена!", "success")

    return redirect(url_for('profile'))

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    app.run(debug=True)