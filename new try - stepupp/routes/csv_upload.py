import os
from flask import Blueprint, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
from routes.auth import role_required
from services.csv_processor import validate_and_parse_csv, process_csv_import

csv_bp = Blueprint('csv_upload', __name__, url_prefix='/api/csv')

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@csv_bp.route('/preview', methods=['POST'])
@role_required('hod', 'staff')
def upload_csv_preview():
    if 'file' not in request.files:
        return jsonify({'success': False, 'errors': ['No file uploaded in request.']}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'errors': ['No file selected.']}), 400

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'errors': ['Invalid file format. Please upload a valid CSV file (.csv).']}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    result = validate_and_parse_csv(filepath)
    # Cache valid data in session for import confirmation step
    if result.get('success') and result.get('valid_data'):
        session['cached_csv_valid_data'] = result['valid_data']

    return jsonify(result)

@csv_bp.route('/import', methods=['POST'])
@role_required('hod', 'staff')
def import_csv_data():
    valid_data = session.get('cached_csv_valid_data')
    if not valid_data:
        # Fall back to request payload if provided directly
        req_data = request.get_json() or {}
        valid_data = req_data.get('valid_data')

    if not valid_data:
        return jsonify({'success': False, 'errors': ['No valid CSV data available to import. Please preview first.']}), 400

    res = process_csv_import(valid_data)
    # Clear cache
    session.pop('cached_csv_valid_data', None)
    
    return jsonify({
        'success': True,
        'message': f"Successfully imported {res['imported_records']} academic records into MySQL database!",
        'imported_count': res['imported_records']
    })
