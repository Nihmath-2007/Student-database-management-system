# Mohamed Sathak Engineering College - Information Technology Department
## Student Academic Analytics & Management Platform

A full-stack, responsive, professional **Student Academic Analytics & Management Website** designed for the **Information Technology (IT) Department** of **Mohamed Sathak Engineering College** (Autonomous Institution, Kilakarai).

The application connects to MySQL (with automatic local SQLite fallback for seamless execution) and provides role-based analytics, dynamic rule-based insights, Chart.js visualizations, automated Pandas CSV processing, and export reports.

---

## 🌟 Technology Stack

- **Backend**: Python 3.14, Flask, REST API Architecture, Flask-Session
- **Database**: MySQL / SQLite (with dual engine fallback), mysql-connector-python, SQLAlchemy
- **Data Analytics Engine**: Pandas, NumPy
- **Frontend**: HTML5, Vanilla CSS3 (Custom Design System in `rgb(19, 29, 59)` Navy & `rgb(255, 79, 1)` Orange Theme), Bootstrap 5, FontAwesome, Chart.js
- **Environment**: python-dotenv

---

## 🔑 User Roles & Demo Credentials

| Role | Username | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **HOD** | `hod` | `hod123` | Full IT Department wide view, analytics, student directory, reports, CSV ingest |
| **Staff** | `staff1` to `staff6` | `staff123` | Subject-restricted analytics for assigned subjects and enrolled students |
| **Student** | `911524205001` | `student123` | Self-restricted academic KPIs, marks, attendance, and progress trend timeline |

---

## 🚀 Key Features

1. **Top College Branding Header**:
   - Features Mohamed Sathak Engineering College header banner (Autonomous Institution, NAAC A+, NBA CSE|IT Accredited, TNEA Code 5907).
2. **Color Palette**:
   - Primary Dark Navy: `rgb(19, 29, 59)`
   - Primary Electric Orange: `rgb(255, 79, 1)`
3. **Data Analytics Focus**:
   - Real-time Pandas-calculated KPIs (Total Students, Total Staff, Total Subjects, Avg Attendance, Avg Marks, Students Below 75% Attendance, Students At Risk, Overall Pass Rate).
   - Dynamic Rule-Based AI Statements ("Database Management System has lowest average marks", "18 students currently below 75%", etc.).
   - Chart.js interactive Bar, Doughnut/Pie, and Line trend charts.
4. **CSV Upload & Ingest Engine**:
   - Automated row validation using Pandas (checks missing values, invalid marks, attendance > 100%, duplicate records, unrecognized register numbers).
   - Instant preview modal and one-click database import which auto-refreshes all charts and dashboard KPIs.
5. **Role-Based Access Control (RBAC)**:
   - Enforced strictly on backend routes via `@role_required` Flask decorators.

---

## 🛠️ Quick Start Instructions

1. **Activate Virtual Environment**:
   ```bash
   python -m venv venv
   # Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Database Seeding**:
   The application automatically reads `railway_students.sql`, `railway_staff.sql`, `railway_subjects.sql`, `railway_attendance.sql`, and `railway_internal_marks.sql` to populate the database on start. You can also run:
   ```bash
   python database/seed_data.py
   ```

4. **Run the Application**:
   ```bash
   python app.py
   ```
   Open your browser at `http://127.0.0.1:5000`.

---

## 📂 Project Structure

```text
student-analytics/
├── app.py                      # Main Flask Application
├── requirements.txt            # Python Dependencies
├── .env                        # Active Environment Variables
├── .env.example                # Example Deployment Env Config
├── Procfile                    # Web server deployment profile
├── config/
│   └── database.py             # Dual MySQL/SQLite Connection Handler
├── database/
│   ├── seed_data.py            # SQL Dump Parser & Database Seeder
│   └── railway_*.sql           # Original SQL Dumps
├── routes/
│   ├── auth.py                 # Login / Logout & RBAC Decorators
│   ├── hod.py                  # HOD Panel API & Pages
│   ├── staff.py                # Staff Panel API & Pages
│   ├── student.py              # Student Panel API & Pages
│   └── csv_upload.py           # CSV Validation & Upload API
├── services/
│   ├── analytics.py            # Pandas Analytics & Dynamic Insights Engine
│   ├── csv_processor.py        # CSV Row Validation Pipeline
│   └── database_service.py     # SQL Data Aggregation Queries
├── static/
│   ├── css/style.css           # Custom MSEC Theme (Navy & Orange)
│   └── js/                     # Chart.js Visualizers & Utils
└── templates/                  # Jinja2 HTML Templates
```
