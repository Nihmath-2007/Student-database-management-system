import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config.database import execute_query
from services.cache_service import api_cache

# ... Priority configuration ...

PRIORITY_MAP = {
    'urgent': {'weight': 1, 'label': 'URGENT', 'icon': 'fa-solid fa-triangle-exclamation', 'class': 'priority-urgent'},
    'high': {'weight': 2, 'label': 'HIGH PRIORITY', 'icon': 'fa-solid fa-bullhorn', 'class': 'priority-high'},
    'medium': {'weight': 3, 'label': 'NOTICE', 'icon': 'fa-solid fa-circle-info', 'class': 'priority-medium'},
    'low': {'weight': 4, 'label': 'REMINDER', 'icon': 'fa-solid fa-bell', 'class': 'priority-low'}
}

AUDIENCE_LABELS = {
    'everyone': 'Everyone (All Roles)',
    'all': 'Everyone (All Roles)',
    'staff': 'Staff Faculty Only',
    'student': 'All Students Only',
    'students': 'All Students Only',
    'First year': '1st Year Students',
    'Second year': '2nd Year Students',
    'Third year': '3rd Year Students',
    'Final year': 'Final Year Students',
    'Section A': 'Section A Students',
    'Section B': 'Section B Students'
}

def format_date_str(date_val):
    if not date_val:
        return ''
    try:
        if isinstance(date_val, str):
            clean_str = date_val.split(' ')[0].split('T')[0]
            dt = datetime.strptime(clean_str, '%Y-%m-%d')
        elif isinstance(date_val, datetime):
            dt = date_val
        else:
            dt = datetime.fromisoformat(str(date_val))
        return dt.strftime('%b %d, %Y')
    except Exception:
        return str(date_val)

def get_audience_label(audience_key):
    if not audience_key:
        return 'Everyone'
    if audience_key in AUDIENCE_LABELS:
        return AUDIENCE_LABELS[audience_key]
    key_clean = str(audience_key).strip()
    if key_clean.startswith('year:'):
        return f"{key_clean.split(':', 1)[1]} Students"
    if key_clean.startswith('section:'):
        return f"Section {key_clean.split(':', 1)[1]} Students"
    return key_clean.capitalize()

def get_active_notifications_for_user(user_id, role, student_id=None):
    """
    Fetches active, unexpired, non-dismissed announcements applicable to the logged-in user.
    HOD sees all active notices.
    Staff sees 'everyone' and 'staff'.
    Student sees 'everyone', 'student', or matching academic year / section.
    """
    if not user_id:
        return []

    cache_key = f"notif_{user_id}_{role}_{student_id}"
    cached = api_cache.get(cache_key)
    if cached is not None:
        return cached

    today_str = datetime.now().strftime('%Y-%m-%d')

    # Query active, non-expired notices not dismissed by this user
    query = """
    SELECT n.*
    FROM notifications n
    WHERE n.is_active = 1
      AND n.expires_at >= %s
      AND n.id NOT IN (
          SELECT nd.notification_id 
          FROM notification_dismissals nd 
          WHERE nd.user_id = %s
      )
    ORDER BY n.created_at DESC
    """
    rows = execute_query(query, (today_str, user_id), fetchall=True) or []
    if not rows:
        api_cache.set(cache_key, [], ttl=300)
        return []

    # Get student year and section if student
    student_year = None
    student_section = None
    if role == 'student' and student_id:
        st_row = execute_query("SELECT year, section FROM students WHERE studentid = %s", (student_id,), fetchone=True)
        if st_row:
            student_year = (st_row.get('year') or '').strip().lower()
            student_section = (st_row.get('section') or '').strip().lower()

    filtered_notices = []
    for row in rows:
        aud = (row.get('audience') or 'everyone').strip().lower()
        priority_key = (row.get('priority') or 'medium').strip().lower()
        if priority_key not in PRIORITY_MAP:
            priority_key = 'medium'

        # Role audience filter
        eligible = False
        if role == 'hod':
            eligible = True
        elif role == 'staff':
            if aud in ('everyone', 'all', 'staff'):
                eligible = True
        elif role == 'student':
            if aud in ('everyone', 'all', 'student', 'students'):
                eligible = True
            elif student_year and (aud == student_year or aud == f"year:{student_year}" or aud in student_year):
                eligible = True
            elif student_section and (aud == f"section {student_section}" or aud == f"section:{student_section}" or aud == student_section):
                eligible = True

        if eligible:
            notice = dict(row)
            p_info = PRIORITY_MAP[priority_key]
            notice['priority_weight'] = p_info['weight']
            notice['priority_label'] = p_info['label']
            notice['priority_icon'] = p_info['icon']
            notice['priority_class'] = p_info['class']
            notice['audience_label'] = get_audience_label(row.get('audience'))
            notice['formatted_expires'] = format_date_str(row.get('expires_at'))
            notice['formatted_created'] = format_date_str(row.get('created_at'))
            filtered_notices.append(notice)

    # Sort primarily by priority weight (1 urgent, 2 high, 3 medium, 4 low), then created_at DESC
    filtered_notices.sort(key=lambda x: (x['priority_weight'], str(x.get('created_at', ''))), reverse=False)

    api_cache.set(cache_key, filtered_notices, ttl=300)
    return filtered_notices

def dismiss_notification_for_user(notification_id, user_id):
    """
    Records a user dismissal for a specific notification.
    """
    check_query = "SELECT id FROM notification_dismissals WHERE notification_id = %s AND user_id = %s"
    existing = execute_query(check_query, (notification_id, user_id), fetchone=True)
    if not existing:
        insert_query = """
        INSERT INTO notification_dismissals (notification_id, user_id, dismissed_at)
        VALUES (%s, %s, %s)
        """
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        execute_query(insert_query, (notification_id, user_id, now_str), commit=True)
    api_cache.invalidate('notif_')
    api_cache.invalidate('admin_notifs')
    return True

def create_notification(title, message, audience, priority, expires_at, created_by=None):
    """
    Creates a new HOD notification announcement.
    """
    query = """
    INSERT INTO notifications (title, message, audience, priority, expires_at, created_by, is_active)
    VALUES (%s, %s, %s, %s, %s, %s, 1)
    """
    res = execute_query(query, (title, message, audience, priority, expires_at, created_by), commit=True)
    api_cache.invalidate('notif_')
    api_cache.invalidate('admin_notifs')
    return res

def get_all_notifications_admin():
    """
    Retrieves all notifications (active, inactive, expired) with dismiss count for HOD management.
    """
    cached = api_cache.get('admin_notifs')
    if cached is not None:
        return cached

    query = """
    SELECT n.*,
           COUNT(nd.id) as dismiss_count
    FROM notifications n
    LEFT JOIN notification_dismissals nd ON n.id = nd.notification_id
    GROUP BY n.id
    ORDER BY n.created_at DESC
    """
    rows = execute_query(query, fetchall=True) or []
    today_str = datetime.now().strftime('%Y-%m-%d')
    results = []

    for r in rows:
        item = dict(r)
        priority_key = (item.get('priority') or 'medium').strip().lower()
        if priority_key not in PRIORITY_MAP:
            priority_key = 'medium'

        p_info = PRIORITY_MAP[priority_key]
        item['priority_weight'] = p_info['weight']
        item['priority_label'] = p_info['label']
        item['priority_icon'] = p_info['icon']
        item['priority_class'] = p_info['class']
        item['audience_label'] = get_audience_label(item.get('audience'))
        item['formatted_expires'] = format_date_str(item.get('expires_at'))
        item['formatted_created'] = format_date_str(item.get('created_at'))

        # Determine real-time status
        expires_date = str(item.get('expires_at') or '').split(' ')[0]
        if item.get('is_active') == 0:
            item['status_badge'] = 'Inactive'
            item['status_class'] = 'bg-secondary'
        elif expires_date < today_str:
            item['status_badge'] = 'Expired'
            item['status_class'] = 'bg-danger'
        else:
            item['status_badge'] = 'Active'
            item['status_class'] = 'bg-success'

        results.append(item)

    api_cache.set('admin_notifs', results, ttl=30)
    return results

def delete_notification(notification_id):
    """
    Permanently deletes a notification and its dismissal history.
    """
    execute_query("DELETE FROM notification_dismissals WHERE notification_id = %s", (notification_id,), commit=True)
    execute_query("DELETE FROM notifications WHERE id = %s", (notification_id,), commit=True)
    api_cache.invalidate('notif_')
    api_cache.invalidate('admin_notifs')
    return True

def toggle_notification_active(notification_id):
    """
    Toggles the active state of a notification.
    """
    row = execute_query("SELECT is_active FROM notifications WHERE id = %s", (notification_id,), fetchone=True)
    if not row:
        return False
    new_state = 0 if row['is_active'] == 1 else 1
    execute_query("UPDATE notifications SET is_active = %s WHERE id = %s", (new_state, notification_id), commit=True)
    api_cache.invalidate('notif_')
    api_cache.invalidate('admin_notifs')
    return new_state
