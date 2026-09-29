import os
from flask import Flask, render_template, redirect, url_for, session, jsonify
from dotenv import load_dotenv

load_dotenv(override=True)

from config.database import SECRET_KEY
from database.seed_data import init_db

# Initialize Flask Application
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 15 * 1024 * 1024  # 15 MB max upload limit
NOTES_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'notes')
os.makedirs(NOTES_UPLOAD_DIR, exist_ok=True)
app.config['NOTES_UPLOAD_DIR'] = NOTES_UPLOAD_DIR

GALLERY_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'gallery')
os.makedirs(GALLERY_UPLOAD_DIR, exist_ok=True)
app.config['GALLERY_UPLOAD_DIR'] = GALLERY_UPLOAD_DIR

# Register Blueprints
from routes.auth import auth_bp, login_required
from routes.hod import hod_bp
from routes.staff import staff_bp
from routes.student import student_bp
from routes.csv_upload import csv_bp
from routes.notifications import notifications_bp
from services.notification_service import get_active_notifications_for_user
from config.database import fetch_one, fetch_all
from flask import send_from_directory, flash

app.register_blueprint(auth_bp)
app.register_blueprint(hod_bp)
app.register_blueprint(staff_bp)
app.register_blueprint(student_bp)
app.register_blueprint(csv_bp)
app.register_blueprint(notifications_bp)

# Injects active announcements into base.html on every portal page
@app.context_processor
def inject_notifications():
    user_id = session.get('user_id')
    if not user_id:
        return {'active_notifications': []}
    role = session.get('role')
    student_id = session.get('student_id')
    try:
        active_notifications = get_active_notifications_for_user(user_id, role, student_id)
    except Exception as e:
        print(f"Notice: notifications context processor: {e}")
        active_notifications = []
    return {'active_notifications': active_notifications}


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

@app.route('/notes/download/<int:note_id>')
@login_required('student', 'staff', 'hod')
def download_note(note_id):
    """
    Serves a subject note file with its original filename via send_from_directory.
    Accessible by student and staff roles. Verifies note existence first.
    """
    note = fetch_one("SELECT * FROM notes WHERE id = %s", (note_id,))
    if not note:
        flash("The requested subject note was not found.", "danger")
        if session.get('role') == 'staff':
            return redirect(url_for('staff.dashboard'))
        return redirect(url_for('student.dashboard'))

    stored_name = os.path.basename(note['stored_path'])
    notes_dir = app.config.get('NOTES_UPLOAD_DIR', os.path.join(app.root_path, 'uploads', 'notes'))
    file_path = os.path.join(notes_dir, stored_name)

    if not os.path.isfile(file_path):
        flash("The note file is missing from the server storage.", "danger")
        if session.get('role') == 'staff':
            return redirect(url_for('staff.dashboard'))
        return redirect(url_for('student.dashboard'))

    return send_from_directory(
        notes_dir,
        stored_name,
        download_name=note['filename'],
        as_attachment=True
    )

@app.route('/gallery')
@login_required('student', 'staff', 'hod')
def gallery():
    """
    Renders the public departmental event photo gallery with a responsive grid
    and CSS-only lightbox for enlarged views.
    """
    photos = fetch_all("SELECT * FROM gallery ORDER BY uploaded_at DESC")
    return render_template('gallery.html', photos=photos)

@app.route('/api/query/<int:query_id>/audit')
@login_required('student', 'staff', 'hod')
def get_query_audit_trail(query_id):
    """
    Returns query details and complete immutable audit trail for a specific mark correction request.
    Verifies role-based access permissions:
    - Students can only view their own queries.
    - Staff can only view queries for their assigned subjects.
    - HOD has full departmental oversight.
    """
    from services.correction_service import get_query_details, get_audit_trail_for_request
    role = session.get('role')
    user_student_id = session.get('student_id')
    user_staff_id = session.get('staff_id')

    query_details = get_query_details(query_id)
    if not query_details:
        return jsonify({'error': 'Mark correction query not found.'}), 404

    if role == 'student' and query_details['student_id'] != user_student_id:
        return jsonify({'error': 'Unauthorized to view this query.'}), 403
    if role == 'staff' and query_details['staff_id'] != user_staff_id:
        return jsonify({'error': 'Unauthorized to view queries outside your subjects.'}), 403

    audit_trail = get_audit_trail_for_request(query_id)
    return jsonify({
        'query': query_details,
        'audit_trail': audit_trail
    })

@app.errorhandler(413)
def request_entity_too_large(e):
    flash("Upload failed: File size exceeds the maximum limit. Please upload a smaller file.", "danger")
    role = session.get('role')
    if role == 'staff':
        
        return redirect(url_for('staff.dashboard'))
    elif role == 'hod':
        return redirect(url_for('hod.dashboard'))
    return redirect(url_for('index'))

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
