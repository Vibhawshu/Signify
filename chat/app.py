from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, emit
from flask_session import Session
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    manage_session=False,
    ping_timeout=30,
    ping_interval=25
)

active_users = set()
typing_users = set()

@app.route('/', methods=['GET', 'POST'])
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username'].strip()
        
        if not username:
            return render_template('login.html', error="Username cannot be empty")
        
        if len(username) > 20:
            return render_template('login.html', error="Username too long (max 20 chars)")
        
        if username in active_users:
            return render_template('login.html', error="Username already taken. Try another.")
        
        session['username'] = username
        active_users.add(username)
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'])


@app.route('/<page_name>')
def dynamic_page(page_name):
    valid_pages = ['practice', 'learn', 'search', 'help', 'sentences', 'words','alphabet-challenge','matching-game', 'search', 'help', 'sentences', 'words','alphabet']  # Add all your pages
    if page_name in valid_pages:
        if 'username' not in session:
            return redirect(url_for('login'))
        return render_template(f'{page_name}.html', username=session['username'])
    return "Page not found", 404

@app.route('/templates/assets/<path:filename>')
def custom_assets(filename):
    return send_from_directory(os.path.join(app.root_path, 'templates', 'assets'), filename)


@app.route('/chat')
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html', username=session['username'])

@app.route('/logout', methods=['POST'])
def logout():
    username = session.pop('username', None)
    if username in active_users:
        active_users.remove(username)
    if username in typing_users:
        typing_users.remove(username)
    return redirect(url_for('login'))

@socketio.on('connect')
def handle_connect():
    username = session.get('username')
    if username:
        emit('message', {
            'username': 'System',
            'message': f'{username} has joined the chat',
            'timestamp': datetime.now().strftime('%H:%M')
        }, broadcast=True)

@socketio.on('message')
def handle_message(data):
    username = session.get('username')
    if not username:
        return
    
    message = data.get('message', '').strip()
    if not message:
        return
    
    emit('message', {
        'username': username,
        'message': message,
        'timestamp': datetime.now().strftime('%H:%M')
    }, broadcast=True)

@socketio.on('typing')
def handle_typing():
    username = session.get('username')
    if username and username not in typing_users:
        typing_users.add(username)
        emit('userTyping', username, broadcast=True)

@socketio.on('stopTyping')
def handle_stop_typing():
    username = session.get('username')
    if username and username in typing_users:
        typing_users.remove(username)

@socketio.on('disconnect')
def handle_disconnect():
    username = session.get('username')
    if username:
        if username in active_users:
            active_users.remove(username)
        if username in typing_users:
            typing_users.remove(username)
        
        emit('message', {
            'username': 'System',
            'message': f'{username} has left the chat',
            'timestamp': datetime.now().strftime('%H:%M')
        }, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)