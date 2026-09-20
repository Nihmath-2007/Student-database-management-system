import os
from flask import Flask, render_template, redirect, url_for, session
from dotenv import load_dotenv

load_dotenv()

from config.database import SECRET_KEY
from database.seed_data import init_db

# Initialize Flask Application
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload limit

# Register Blueprints
from routes.auth import auth_bp
from routes.hod import hod_bp
from routes.staff import staff_bp
from routes.student import student_bp
from routes.csv_upload import csv_bp

app.register_blueprint(auth_bp)
app.register_blueprint(hod_bp)
app.register_blueprint(staff_bp)
app.register_blueprint(student_bp)
app.register_blueprint(csv_bp)

@app.route('/')
def index():
    if 'user_id' in session:
        role = session.get('role')
        if role == 'hod':
            return redirect(url_for('hod.dashboard'))
        elif role == 'staff':
            return redirect(url_for('staff.dashboard'))
        elif role == 'student':
            return redirect(url_for('student.dashboard'))
    return redirect(url_for('auth.login'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html', error=str(e)), 500

# Seed database on startup if SQLite or needed
with app.app_context():
    try:
        init_db()
    except Exception as e:
        print(f"Database initialization log: {e}")

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
