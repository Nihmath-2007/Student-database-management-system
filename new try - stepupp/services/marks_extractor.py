import os
import re
<<<<<<< HEAD
try:
    import cv2
except ImportError:
    cv2 = None
=======
import cv2
>>>>>>> 0428c9a (Update project)
import numpy as np
from PIL import Image

def preprocess_image_for_ocr(img_input):
    """
    Applies OpenCV pre-processing to improve OCR accuracy:
    1. Converts to grayscale
    2. Denoises
    3. Calculates deskew angle and rotates
    4. Applies Otsu / Adaptive thresholding
    """
<<<<<<< HEAD
    if cv2 is None:
        raise ImportError("OpenCV ('cv2') is required for OCR image processing. Please install it using 'pip install opencv-python'.")

=======
>>>>>>> 0428c9a (Update project)
    # 1. Convert input to cv2 numpy array (BGR)
    if isinstance(img_input, str):
        cv_img = cv2.imread(img_input)
    elif isinstance(img_input, Image.Image):
        cv_img = cv2.cvtColor(np.array(img_input), cv2.COLOR_RGB2BGR)
    elif isinstance(img_input, np.ndarray):
        cv_img = img_input
    else:
        raise ValueError("Unsupported image type for OCR preprocessing")

    if cv_img is None:
        raise ValueError("Failed to load image for preprocessing")

    # 2. Grayscale
    if len(cv_img.shape) == 3:
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = cv_img.copy()

    # 3. Deskew calculation
    try:
        # Invert colors so text is white on black background for contour/bounding box analysis
        inv_thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(inv_thresh > 0))
        if coords.size > 0:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            elif angle > 45:
                angle = 90 - angle
            else:
                angle = -angle

            # Only rotate if skew is notable (> 0.5 deg) and not extreme (< 45 deg)
            if 0.5 < abs(angle) < 45:
                (h, w) = gray.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    except Exception as e:
        print(f"Deskew warning: {e}")

    # 4. Contrast enhancement & Denoise
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    # 5. Otsu Thresholding
    thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    return thresh


def _find_tesseract_cmd():
    """Locates the tesseract executable across PATH and known Windows installations."""
    import shutil
    which_cmd = shutil.which("tesseract")
    if which_cmd:
        return which_cmd

    custom_env = os.getenv("TESSERACT_CMD")
    if custom_env and os.path.isfile(custom_env):
        return custom_env

    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
<<<<<<< HEAD
        r"C:\Tesseract-OCR\tesseract.exe",
        os.path.join(os.getcwd(), "tesseract-installer.exe"),
=======
>>>>>>> 0428c9a (Update project)
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract"
    ]
    for path in candidates:
<<<<<<< HEAD
        if os.path.isfile(path) and path.endswith("tesseract.exe"):
=======
        if os.path.isfile(path):
>>>>>>> 0428c9a (Update project)
            return path
    return None


def is_absent_value(val_str):
    """
    Checks if an extracted mark string denotes an absent student.
    Treats 'AB', 'A', '-', 'ABSENT', 'ABS', 'NA', 'N/A', '', 'A/B' as absent.
    """
    if val_str is None:
        return True
    s = str(val_str).strip().upper()
    if s in {'AB', 'A', '-', '--', 'ABS', 'ABSENT', 'NA', 'N/A', 'A/B', 'AAA', 'BLANK', ''}:
        return True
    return False


def clean_mark_value(val_str):
    """
    Extracts numerical mark or identifies absence.
    Returns (cleaned_mark_float_or_None, is_absent_bool)
    """
    if val_str is None:
        return None, True

    s = str(val_str).strip()
    if is_absent_value(s):
        return None, True

    # Remove trailing characters or annotations (e.g. "84/100" -> "84", "84*" -> "84")
    if '/' in s:
        s = s.split('/')[0].strip()

    # Search for numeric value
    match = re.search(r'[-+]?\d*\.?\d+', s)
    if match:
        try:
            val = float(match.group())
            return val, False
        except ValueError:
            pass

    return None, is_absent_value(s)


def parse_text_line(line):
    """
    Parses a single line of text from marks sheet.
    Handles:
    - Format 1: 'Register No  Name  Mark' (e.g. '911524205001 ABICHETHRA P 84' or '911524205001 ABICHETHRA P AB')
    - Format 2: 'Name  Mark' (e.g. 'ABICHETHRA P 84' or 'ABICHETHRA P A')
    - Format 3: 'Register No  Mark' (e.g. '911524205001 84')
    Filters out common table header rows.
    """
    line = line.strip()
    if not line or len(line) < 2:
        return None

    # Skip obvious headers and titles
    header_keywords = [
        'REGISTER', 'REG.NO', 'REG NO', 'ROLL NO', 'STUDENT NAME', 'NAME OF THE',
        'MARKS', 'MARK OBTAINED', 'MAX MARKS', 'TEST NO', 'INTERNAL TEST',
        'SUBJECT', 'SEMESTER', 'DEPARTMENT', 'ATTENDANCE', 'SIGNATURE', 'PAGE'
    ]
    upper_line = line.upper()
    if any(k in upper_line for k in ['REGISTER NUMBER', 'STUDENT NAME', 'MARKS OBTAINED', 'INTERNAL ASSESSMENT']):
        # If line contains 2 or more header keywords, it's definitely a header row
        match_count = sum(1 for k in header_keywords if k in upper_line)
        if match_count >= 2:
            return None

    # Tokenize line by whitespace or tab
    tokens = re.split(r'[\t,;|]|\s{2,}', line)
    tokens = [t.strip() for t in tokens if t.strip()]

    # If splitting by multiple spaces yielded only 1 token, split by single space
    if len(tokens) <= 1:
        tokens = line.split()

    if len(tokens) < 2:
        return None

    # Check for leading serial number (e.g. "1.", "1", "01")
    if tokens[0].rstrip('.').isdigit() and len(tokens[0].rstrip('.')) <= 3 and len(tokens) > 2:
        tokens = tokens[1:]

    # Last token is usually the Mark or Absent indicator
    raw_mark_token = tokens[-1]
    cleaned_mark, is_absent = clean_mark_value(raw_mark_token)

    # If the last token couldn't be parsed as a number or absent, check if line ends with mark
    if cleaned_mark is None and not is_absent:
        # Check if the last token is something like "84.00" or has trailing punctuation
        m = re.search(r'(\d+\.?\d*|AB|A|-)$', line.strip(), re.IGNORECASE)
        if m:
            raw_mark_token = m.group(1)
            cleaned_mark, is_absent = clean_mark_value(raw_mark_token)
            # Reconstruct preceding tokens
            rem_text = line[:m.start()].strip()
            tokens = rem_text.split()
        else:
            return None

    # The remaining tokens represent the Student Identifier (Regno and/or Name)
    remaining_tokens = tokens[:-1] if tokens[-1] == raw_mark_token else tokens
    if not remaining_tokens:
        return None

    # Check if first remaining token is a register number (long number, usually 8-16 digits)
    first_token = re.sub(r'[^a-zA-Z0-9]', '', remaining_tokens[0])
    raw_regno = None
    raw_name = ""

    if (first_token.isdigit() and len(first_token) >= 6) or (len(first_token) >= 8 and any(c.isdigit() for c in first_token)):
        raw_regno = first_token
        raw_name = " ".join(remaining_tokens[1:]).strip()
    else:
        raw_name = " ".join(remaining_tokens).strip()

    # Clean raw_name
    raw_name = re.sub(r'^[0-9]+[\.\-\)]\s*', '', raw_name).strip()

    return {
        'raw_identifier': raw_regno or raw_name,
        'raw_regno': raw_regno,
        'raw_name': raw_name,
        'raw_mark': raw_mark_token,
        'cleaned_mark': cleaned_mark,
        'is_absent': is_absent,
        'line_text': line
    }


def extract_from_pdf_text(pdf_path):
    """
    Extracts table rows and lines from selectable-text PDF using pdfplumber.
    """
    import pdfplumber

    extracted_records = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # 1. Try table extraction first
            tables = page.extract_tables()
            table_found_rows = 0

            if tables:
                for table in tables:
                    if not table or len(table) < 2:
                        continue

                    # Determine column indices from header row if available
                    header_row = [str(c or '').strip().upper() for c in table[0]]
                    regno_idx = -1
                    name_idx = -1
                    mark_idx = -1

                    for idx, cell in enumerate(header_row):
                        if any(w in cell for w in ['REG', 'ROLL', 'REGISTER']):
                            regno_idx = idx
                        elif any(w in cell for w in ['NAME', 'STUDENT']):
                            name_idx = idx
                        elif any(w in cell for w in ['MARK', 'SCORE', 'OBTAINED', 'TOTAL']):
                            mark_idx = idx

                    # Process table data rows
                    start_row = 1 if (regno_idx != -1 or name_idx != -1 or mark_idx != -1) else 0
                    for row in table[start_row:]:
                        if not row or not any(row):
                            continue

                        # Clean cells
                        cells = [str(c or '').strip() for c in row if c is not None]
                        if not cells:
                            continue

                        # If columns were identified:
                        if mark_idx != -1 and mark_idx < len(row):
                            r_mark = str(row[mark_idx] or '').strip()
                            r_reg = str(row[regno_idx] or '').strip() if regno_idx != -1 and regno_idx < len(row) else None
                            r_name = str(row[name_idx] or '').strip() if name_idx != -1 and name_idx < len(row) else ''

                            if not r_reg and not r_name:
                                continue

                            c_mark, is_ab = clean_mark_value(r_mark)
                            if c_mark is not None or is_ab:
                                extracted_records.append({
                                    'raw_identifier': r_reg or r_name,
                                    'raw_regno': r_reg if r_reg and any(ch.isdigit() for ch in r_reg) else None,
                                    'raw_name': r_name,
                                    'raw_mark': r_mark,
                                    'cleaned_mark': c_mark,
                                    'is_absent': is_ab,
                                    'line_text': " | ".join([c for c in [r_reg, r_name, r_mark] if c])
                                })
                                table_found_rows += 1
                                continue

                        # Fallback for table row without identified header: join and parse
                        joined = "  ".join(cells)
                        parsed = parse_text_line(joined)
                        if parsed:
                            extracted_records.append(parsed)
                            table_found_rows += 1

            # 2. If table extraction yielded few or no records, parse raw text
            if table_found_rows == 0:
                raw_text = page.extract_text() or ""
                lines = raw_text.splitlines()
                for line in lines:
                    parsed = parse_text_line(line)
                    if parsed:
                        extracted_records.append(parsed)

    return extracted_records


def convert_pdf_to_images(pdf_path):
    """
    Converts PDF pages into PIL Images.
    Uses pdf2image if poppler is installed, otherwise falls back to pypdfium2.
    """
    images = []
    # 1. Try pdf2image first
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(pdf_path, dpi=250)
        if images:
            return images
    except Exception as e:
        print(f"pdf2image fallback to pypdfium2 ({e})")

    # 2. Resilient fallback using pypdfium2 (pure Python/precompiled C, no external Poppler required)
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(pdf_path)
        for page_index in range(len(pdf)):
            page = pdf[page_index]
            # Render at 2.5x resolution for sharp OCR
            pil_image = page.render(scale=2.5).to_pil()
            images.append(pil_image)
        return images
    except Exception as e:
        raise RuntimeError(f"Failed to convert PDF pages to images: {e}")


def extract_from_image_ocr(image_input):
    """
    Applies OpenCV pre-processing and extracts text using pytesseract OCR.
    """
    import pytesseract

    tess_path = _find_tesseract_cmd()
    if tess_path:
        pytesseract.pytesseract.tesseract_cmd = tess_path
    else:
<<<<<<< HEAD
        import shutil
        if not shutil.which("tesseract"):
            raise FileNotFoundError(
                "Tesseract OCR executable was not found on the system.\n\n"
                "To resolve this, please choose one of the following:\n"
                "1. Double-click 'install_tesseract.bat' in your project root to run the installer, or run:\n"
                "   winget install UB-Mannheim.TesseractOCR\n"
                "2. OR add GEMINI_API_KEY in your .env file to enable Google Gemini Vision AI (ideal for handwritten mark sheets)."
=======
        # Check if pytesseract default works, otherwise raise actionable error
        import shutil
        if not shutil.which("tesseract"):
            raise FileNotFoundError(
                "Tesseract OCR executable was not found on the system. "
                "Please install Tesseract OCR or upload a selectable-text PDF / provide a Vision API key."
>>>>>>> 0428c9a (Update project)
            )

    processed_cv = preprocess_image_for_ocr(image_input)

    # Use PSM 6 (Assume a single uniform block of text) and PSM 4 fallback
    custom_config = r'--oem 3 --psm 6'
    ocr_text = pytesseract.image_to_string(processed_cv, config=custom_config)

    records = []
    for line in ocr_text.splitlines():
        parsed = parse_text_line(line)
        if parsed:
            records.append(parsed)

    # If PSM 6 yielded very few lines, try PSM 4 (single column variable text)
    if len(records) < 3:
        alt_text = pytesseract.image_to_string(processed_cv, config=r'--oem 3 --psm 4')
        alt_records = []
        for line in alt_text.splitlines():
            parsed = parse_text_line(line)
            if parsed:
                alt_records.append(parsed)
        if len(alt_records) > len(records):
            records = alt_records

    return records


def extract_with_vision_api(file_path_or_image, api_key=None, provider="gemini"):
    """
    Modular vision / LLM API extractor function for images and scanned PDFs.
<<<<<<< HEAD
    Uses Google Gemini Vision API to accurately extract handwritten marks sheets and tabular data.
    """
    import io
    import json
    import base64
    import urllib.request
    import urllib.error

    key = api_key or os.getenv('GEMINI_API_KEY') or os.getenv('VISION_API_KEY')
    if not key:
        raise ValueError("No Vision API key provided. Set GEMINI_API_KEY in your .env file.")

    # Convert input to JPEG bytes
    if isinstance(file_path_or_image, str):
        with open(file_path_or_image, 'rb') as f:
            img_bytes = f.read()
    elif isinstance(file_path_or_image, Image.Image):
        buf = io.BytesIO()
        file_path_or_image.save(buf, format='JPEG')
        img_bytes = buf.getvalue()
    elif hasattr(file_path_or_image, 'read'):
        img_bytes = file_path_or_image.read()
    else:
        raise ValueError("Unsupported input format for Vision API.")

    b64_data = base64.b64encode(img_bytes).decode('utf-8')

    prompt = (
        "You are an expert academic data extraction system. "
        "Extract all student marks from this mark statement table. "
        "Carefully read all rows and parallel/side-by-side tables if present. "
        "For each student row, extract: \n"
        "- 'raw_identifier': register number (e.g. '911524205001' or '5001') or student name\n"
        "- 'raw_regno': the register number digits if available, else null\n"
        "- 'raw_name': the student name in uppercase\n"
        "- 'raw_mark': the marks obtained as written (e.g. '46', '48', 'AB', 'A')\n"
        "- 'cleaned_mark': numerical score as float or int, or null if absent\n"
        "- 'is_absent': boolean true if absent ('AB', 'A', '-', 'ABSENT'), false otherwise\n\n"
        "Return ONLY a valid JSON array of these objects."
    )

    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": b64_data
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.1
        }
    }

    req_data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp_body = resp.read().decode('utf-8')
            res_json = json.loads(resp_body)
            content = res_json['candidates'][0]['content']['parts'][0]['text']
            clean_content = re.sub(r'^```(?:json)?\s*', '', content.strip())
            clean_content = re.sub(r'\s*```$', '', clean_content.strip())
            records = json.loads(clean_content)

            formatted_records = []
            for r in records:
                c_mark, is_ab = clean_mark_value(r.get('raw_mark'))
                reg = str(r.get('raw_regno') or '').strip() or None
                name = str(r.get('raw_name') or '').strip()
                ident = str(r.get('raw_identifier') or reg or name).strip()
                formatted_records.append({
                    'raw_identifier': ident,
                    'raw_regno': reg,
                    'raw_name': name,
                    'raw_mark': str(r.get('raw_mark', '')),
                    'cleaned_mark': c_mark if c_mark is not None else r.get('cleaned_mark'),
                    'is_absent': is_ab or bool(r.get('is_absent')),
                    'line_text': f"{reg or ''} {name} {r.get('raw_mark', '')}".strip()
                })
            return formatted_records
    except urllib.error.HTTPError as e:
        err_text = e.read().decode('utf-8', errors='ignore')
        raise RuntimeError(f"Gemini Vision API error ({e.code}): {err_text}")
    except Exception as e:
        raise RuntimeError(f"Vision API extraction failed: {str(e)}")
=======
    Allows easy swapping with external vision APIs (Gemini or OpenAI).
    """
    key = api_key or os.getenv('GEMINI_API_KEY') or os.getenv('VISION_API_KEY') or os.getenv('OPENAI_API_KEY')
    if not key:
        raise ValueError("No Vision/LLM API key provided. Set GEMINI_API_KEY or OPENAI_API_KEY.")

    # Implementation hook for external vision model
    # Formulates JSON output: [{"raw_identifier": ..., "raw_name": ..., "raw_regno": ..., "raw_mark": ..., "is_absent": ...}]
    # Pluggable placeholder that can be invoked whenever API key is supplied by user
    raise NotImplementedError("Vision API integration is pluggable and ready to connect when API key is provided.")
>>>>>>> 0428c9a (Update project)


def extract_marks_from_file(file_path, filename):
    """
    Main extraction orchestrator:
    1. For PDF files: First tries selectable-text extraction with pdfplumber.
<<<<<<< HEAD
    2. If PDF has no text (scanned PDF), renders pages to images and runs Gemini Vision or OCR.
    3. For Image files (JPG, JPEG, PNG):
       - If GEMINI_API_KEY is configured, uses Gemini Vision AI (ideal for handwritten mark sheets).
       - Otherwise, falls back to OpenCV pre-processing and local Tesseract OCR.
    Returns: list of extracted student mark records.
    """
    ext = os.path.splitext(filename)[1].lower()
    has_vision_key = bool(os.getenv('GEMINI_API_KEY') or os.getenv('VISION_API_KEY'))
=======
    2. If PDF has no text (scanned PDF), renders pages to images and runs OCR.
    3. For Image files (JPG, JPEG, PNG), applies OpenCV pre-processing and OCR.
    Returns: list of extracted student mark records.
    """
    ext = os.path.splitext(filename)[1].lower()
>>>>>>> 0428c9a (Update project)

    if ext == '.pdf':
        try:
            records = extract_from_pdf_text(file_path)
            if records and len(records) > 0:
                return records
<<<<<<< HEAD
            print("PDF has no selectable text table rows; proceeding to image OCR / Vision extraction...")
        except Exception as e:
            print(f"pdfplumber text extraction failed or empty ({e}), falling back to image extraction...")

        # Scanned PDF: convert pages to images then run Vision or OCR
        images = convert_pdf_to_images(file_path)
        all_records = []
        for img in images:
            if has_vision_key:
                try:
                    vision_records = extract_with_vision_api(img)
                    if vision_records:
                        all_records.extend(vision_records)
                        continue
                except Exception as ve:
                    print(f"Gemini Vision API error ({ve}), falling back to Tesseract OCR...")
=======
            print("PDF has no selectable text table rows; proceeding to OCR image extraction...")
        except Exception as e:
            print(f"pdfplumber text extraction failed or empty ({e}), falling back to OCR...")

        # Scanned PDF: convert pages to images then run OCR
        images = convert_pdf_to_images(file_path)
        all_records = []
        for img in images:
>>>>>>> 0428c9a (Update project)
            page_records = extract_from_image_ocr(img)
            all_records.extend(page_records)
        return all_records

    elif ext in ('.jpg', '.jpeg', '.png'):
<<<<<<< HEAD
        if has_vision_key:
            try:
                vision_records = extract_with_vision_api(file_path)
                if vision_records:
                    return vision_records
            except Exception as ve:
                print(f"Gemini Vision API error ({ve}), falling back to Tesseract OCR...")
=======
>>>>>>> 0428c9a (Update project)
        return extract_from_image_ocr(file_path)

    else:
        raise ValueError(f"Unsupported file extension '{ext}'. Only .pdf, .jpg, .jpeg, and .png are allowed.")
