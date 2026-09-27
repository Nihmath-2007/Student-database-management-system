from datetime import datetime
from flask import Blueprint, request, jsonify, session
from routes.auth import login_required, role_required
from services.notification_service import (
    create_notification,
    dismiss_notification_for_user,
    get_all_notifications_admin,
    delete_notification,
    toggle_notification_active
)

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

@notifications_bp.route('/dismiss/<int:notification_id>', methods=['POST'])
@login_required
def dismiss_notification_route(notification_id):
    user_id = session.get('user_id')
    try:
        dismiss_notification_for_user(notification_id, user_id)
        return jsonify({
            'success': True,
            'message': 'Notification dismissed successfully for this session.'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@notifications_bp.route('/create', methods=['POST'])
@role_required('hod')
def create_notification_route():
    data = request.get_json() if request.is_json else request.form
    title = str(data.get('title', '')).strip()
    message = str(data.get('message', '')).strip()
    audience = str(data.get('audience', 'everyone')).strip()
    priority = str(data.get('priority', 'medium')).strip().lower()
    expires_at = str(data.get('expires_at', '')).strip()

    if not title:
        return jsonify({'success': False, 'error': 'Title/Headline is required.'}), 400
    if not message:
        return jsonify({'success': False, 'error': 'Announcement message is required.'}), 400
    if not expires_at:
        return jsonify({'success': False, 'error': 'Expiry date is required.'}), 400

    # Validate date
    try:
        clean_exp = expires_at.split('T')[0]
        dt = datetime.strptime(clean_exp, '%Y-%m-%d')
        # Check if already expired
        today = datetime.now().date()
        if dt.date() < today:
            return jsonify({'success': False, 'error': 'Expiry date cannot be in the past.'}), 400
        expires_at = dt.strftime('%Y-%m-%d')
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid expiry date format. Please use YYYY-MM-DD.'}), 400

    if priority not in ('urgent', 'high', 'medium', 'low'):
        priority = 'medium'

    created_by = session.get('user_id')
    try:
        notif_id = create_notification(title, message, audience, priority, expires_at, created_by)
        return jsonify({
            'success': True,
            'message': 'Announcement published successfully to department notification bar!',
            'notification_id': notif_id
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@notifications_bp.route('/admin-list', methods=['GET'])
@role_required('hod')
def get_admin_notifications_route():
    try:
        notices = get_all_notifications_admin()
        return jsonify({'success': True, 'notifications': notices})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@notifications_bp.route('/<int:notification_id>', methods=['DELETE'])
@role_required('hod')
def delete_notification_route(notification_id):
    try:
        delete_notification(notification_id)
        return jsonify({'success': True, 'message': 'Announcement deleted successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@notifications_bp.route('/<int:notification_id>/toggle', methods=['PATCH'])
@role_required('hod')
def toggle_notification_route(notification_id):
    try:
        new_state = toggle_notification_active(notification_id)
        return jsonify({
            'success': True,
            'is_active': new_state,
            'message': f"Announcement {'activated' if new_state else 'deactivated'}."
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
