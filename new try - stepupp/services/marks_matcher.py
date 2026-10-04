import re
<<<<<<< HEAD
try:
    from rapidfuzz import fuzz
except ImportError:
    import difflib
    class FuzzFallback:
        @staticmethod
        def ratio(s1, s2):
            return difflib.SequenceMatcher(None, str(s1), str(s2)).ratio() * 100
        @staticmethod
        def token_sort_ratio(s1, s2):
            t1 = " ".join(sorted(str(s1).split()))
            t2 = " ".join(sorted(str(s2).split()))
            return difflib.SequenceMatcher(None, t1, t2).ratio() * 100
    fuzz = FuzzFallback()
=======
from rapidfuzz import fuzz
>>>>>>> 0428c9a (Update project)
from config.database import fetch_all, fetch_one

def normalize_text(text):
    """
    Normalizes a name or text string for robust fuzzy comparison:
    - Uppercase
    - Strips all punctuation and symbols (dots, dashes, commas, apostrophes)
    - Collapses multiple whitespace into single space
    """
    if not text:
        return ""
    # Remove all punctuation and symbols
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', str(text))
    # Normalize spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip().upper()
    return cleaned


def normalize_regno(regno):
    """
    Normalizes register numbers by stripping whitespace and non-alphanumeric characters.
    """
    if not regno:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(regno)).strip().upper()


def get_students_for_subject(subject_id):
    """
    Fetches only students belonging to the selected subject's class/semester.
    1. Looks up the subject's semester.
    2. Maps semester to academic year (1,2 -> First year, 3,4 -> Second year, 5,6 -> Third year, 7,8 -> Final year).
    3. Queries students enrolled in that year.
    4. If no students match exact year string, fetches students who already have marks or all students.
    """
    subject = fetch_one("SELECT * FROM subjects WHERE subjectid = %s", (subject_id,))
    if not subject:
        # Fallback to all students
        return fetch_all("SELECT studentid, regno, name, department, year FROM students ORDER BY regno ASC") or []

    semester = int(subject.get('semester') or 5)
    
    # Semester to year mapping
    semester_year_map = {
        1: ['First year', '1st year', 'I year', 'I', 'First Year'],
        2: ['First year', '1st year', 'I year', 'I', 'First Year'],
        3: ['Second year', '2nd year', 'II year', 'II', 'Second Year'],
        4: ['Second year', '2nd year', 'II year', 'II', 'Second Year'],
        5: ['Third year', '3rd year', 'III year', 'III', 'Third Year'],
        6: ['Third year', '3rd year', 'III year', 'III', 'Third Year'],
        7: ['Fourth year', 'Final year', '4th year', 'IV year', 'IV', 'Final Year'],
        8: ['Fourth year', 'Final year', '4th year', 'IV year', 'IV', 'Final Year']
    }
    
    target_years = semester_year_map.get(semester, ['Third year'])
    placeholders = ','.join(['%s'] * len(target_years))
    
    students = fetch_all(
        f"SELECT studentid, regno, name, department, year FROM students WHERE year IN ({placeholders}) ORDER BY regno ASC",
        tuple(target_years)
    )

    # Fallback if student records don't match year strings or are empty
    if not students:
        # Check if students are in internal_marks for this subject
        students = fetch_all("""
            SELECT s.studentid, s.regno, s.name, s.department, s.year 
            FROM students s 
            WHERE s.studentid IN (SELECT DISTINCT student_id FROM internal_marks WHERE subject_id = %s)
            ORDER BY s.regno ASC
        """, (subject_id,))

    if not students:
        students = fetch_all("SELECT studentid, regno, name, department, year FROM students ORDER BY regno ASC") or []

    return students


def match_extracted_rows_to_students(extracted_rows, subject_id, threshold=90.0):
    """
    Matches extracted (identifier, mark) pairs to database students:
    1. Match first by register number (regno) if present.
    2. Otherwise match by name, ignoring case, extra spaces and punctuation,
       using fuzzy matching (rapidfuzz, threshold 90).
    3. Only matches against students in the selected subject's class/semester.
    4. Categorizes status as:
       - 'Matched' (single high confidence match >= 90 or exact regno)
       - 'Needs Review' (low confidence 70-89% or multiple students >= 90%)
       - 'Not Found' (no student found or score < 70%)
    """
    students = get_students_for_subject(subject_id)

    # Build fast lookup indexes
    regno_map = {}
    name_candidates = []

    for s in students:
        clean_reg = normalize_regno(s.get('regno'))
        if clean_reg:
            regno_map[clean_reg] = s

        clean_name = normalize_text(s.get('name'))
        name_candidates.append({
            'student': s,
            'clean_name': clean_name,
            'regno': s.get('regno'),
            'name': s.get('name')
        })

    matched_results = []

    for index, row in enumerate(extracted_rows):
        raw_regno = normalize_regno(row.get('raw_regno'))
        raw_name = row.get('raw_name') or ''
        raw_identifier = row.get('raw_identifier') or ''
        mark_val = row.get('cleaned_mark')
        is_absent = row.get('is_absent', False)

        matched_student = None
        status = 'Not Found'
        confidence = 0.0
        reason = ""

        # =====================================================================
        # STEP 1: MATCH BY REGISTER NUMBER (IF PRESENT)
        # =====================================================================
        if raw_regno:
            # Check exact match
            if raw_regno in regno_map:
                matched_student = regno_map[raw_regno]
                status = 'Matched'
                confidence = 100.0
                reason = f"Matched by Register No: {matched_student['regno']}"
            else:
                # Check partial match on last 4-6 digits if regno format is standard
                suffix_matches = [
                    s for reg, s in regno_map.items()
                    if reg.endswith(raw_regno) or (len(raw_regno) >= 5 and raw_regno.endswith(reg[-5:]))
                ]
                if len(suffix_matches) == 1:
                    matched_student = suffix_matches[0]
                    status = 'Matched'
                    confidence = 96.0
                    reason = f"Matched by Register No suffix: {matched_student['regno']}"
                elif len(suffix_matches) > 1:
                    matched_student = suffix_matches[0]
                    status = 'Needs Review'
                    confidence = 88.0
                    reason = f"Multiple students match regno suffix: {', '.join([s['name'] for s in suffix_matches[:2]])}"

        # =====================================================================
        # STEP 2: MATCH BY NAME (IF NOT MATCHED BY REGNO)
        # =====================================================================
        if not matched_student:
            target_name = normalize_text(raw_name or raw_identifier)
            # Remove digits from target name if any
            target_name = re.sub(r'\d+', '', target_name).strip()

            if not target_name or len(target_name) < 2:
                status = 'Not Found'
                confidence = 0.0
                reason = "No legible student name or register number extracted"
            else:
                # Fuzzy score calculation using rapidfuzz token_sort_ratio and ratio
                scored = []
                for cand in name_candidates:
                    c_name = cand['clean_name']
                    # Token sort ratio handles initial placed at start vs end (e.g. 'P ABICHETHRA' vs 'ABICHETHRA P')
                    ts_score = fuzz.token_sort_ratio(target_name, c_name)
                    # Token set ratio handles extra middle names or initials
                    tset_score = fuzz.token_set_ratio(target_name, c_name)
                    # Standard ratio for tight match
                    r_score = fuzz.ratio(target_name, c_name)

                    combined_score = max(ts_score, (ts_score * 0.7 + tset_score * 0.3), r_score)
                    scored.append({
                        'student': cand['student'],
                        'score': combined_score,
                        'name': cand['name'],
                        'regno': cand['regno']
                    })

                scored.sort(key=lambda x: x['score'], reverse=True)
                top = scored[0] if scored else None

                if top:
                    # Collect all candidates meeting or exceeding the 90.0 threshold
                    high_matches = [c for c in scored if c['score'] >= threshold]

                    if len(high_matches) == 1:
                        matched_student = high_matches[0]['student']
                        status = 'Matched'
                        confidence = round(high_matches[0]['score'], 1)
                        reason = f"Fuzzy name match ({confidence}% confidence)"
                    elif len(high_matches) > 1:
                        # Several possible students with high similarity
                        matched_student = high_matches[0]['student']
                        status = 'Needs Review'
                        confidence = round(high_matches[0]['score'], 1)
                        names = [f"{c['name']} ({c['score']:.0f}%)" for c in high_matches[:3]]
                        reason = f"Multiple possible students: {', '.join(names)}"
                    else:
                        # Below 90 threshold: Check if it meets moderate confidence (>= 70%)
                        if top['score'] >= 70.0:
                            matched_student = top['student']
                            status = 'Needs Review'
                            confidence = round(top['score'], 1)
                            reason = f"Low confidence match ({confidence}% < {threshold}%)"
                        else:
                            matched_student = None
                            status = 'Not Found'
                            confidence = round(top['score'], 1)
                            reason = f"No matching student found (best score: {confidence}%)"

        matched_results.append({
            'row_id': index,
            'extracted_name': row.get('raw_name') or row.get('raw_identifier') or '',
            'extracted_regno': row.get('raw_regno') or '',
            'raw_identifier': row.get('raw_identifier') or '',
            'mark': 'AB' if is_absent else (mark_val if mark_val is not None else row.get('raw_mark', '')),
            'cleaned_mark': mark_val,
            'is_absent': is_absent,
            'status': status,
            'confidence': confidence,
            'reason': reason,
            'matched_student_id': matched_student['studentid'] if matched_student else None,
            'matched_student_name': matched_student['name'] if matched_student else '',
            'matched_regno': matched_student['regno'] if matched_student else '',
            'line_text': row.get('line_text', '')
        })

    return {
        'results': matched_results,
        'eligible_students': [
            {'studentid': s['studentid'], 'regno': s['regno'], 'name': s['name']}
            for s in students
        ]
    }
