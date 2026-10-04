# Mohamed Sathak Engineering College (Autonomous)
## Department of Information Technology
### Student Academic Analytics & Management Platform

A high-performance, full-stack, enterprise-grade **Student Academic Analytics & Management System** custom-engineered for the **Information Technology (IT) Department** of **Mohamed Sathak Engineering College** (Autonomous Institution, Kilakarai - TNEA Code 5907, Accredited by NAAC A+ and NBA).

The platform features a **Dual-Engine Database Architecture** (Cloud MySQL on Railway with automatic local SQLite fallback), role-based dashboards, unified 6-grade visual analytics via Chart.js, a centralized Master Edit Details Hub, automated student data ingestion with encrypted Date of Birth (DOB) authentication, and real-time attendance calculation.

---

## 🌟 Technology Stack

| Component | Technologies |
| :--- | :--- |
| **Backend Framework** | Python 3.14, Flask 3.1.3, Blueprint Modular Routing, REST APIs |
| **Data Engine & Processing** | Pandas 3.0.5, NumPy 2.5.2, OpenPyXL 3.1.5, RapidFuzz 3.0 |
| **Authentication & Security** | Bcrypt 5.0, Werkzeug 3.1, Anti-Brute Force Lockout (5 attempts / 5 min lock), 15-min Inactivity Timeout |
| **Primary Database** | Remote MySQL (Railway Cloud) with Thread-Safe Connection Pool & TCP Keepalive |
| **Fallback Database** | Local SQLite (`student_analytics.db`) optimized with `WAL` journal mode and memory PRAGMAs |
| **Frontend UI/UX** | HTML5, Vanilla CSS3, Bootstrap 5, FontAwesome 6, Chart.js Visualizers |
| **Brand Identity** | Official MSEC Colors: Midnight Navy (`#0b1a30`), Electric Orange (`#f25822`), Light Grey (`#f4f6f9`) |

---

## 🔑 User Roles & Login Credentials

Authentication is strictly enforced on all routes via `@role_required` and `@login_required` decorators.

| Role | Username / Identifier | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | `admin123` | Complete administrative system access, user oversight, and global configurations |
| **HOD** | `hod` | `hod123` | Department-wide analytics, Master Edit Hub, faculty allocations, timetable, reports, and CSV upload |
| **Faculty / Staff** | `staff1` to `staff6` *(or Faculty Name)* | `staff123` | Subject analytics, enrolled student roster, internal marks entry, class attendance, and timetable |
| **Student (62 Enrolled)** | Register Number *(e.g., `911524205001`)* | **Date of Birth** in `DDMMYYYY` *(e.g., `07082007`)* | Personal academic KPIs, attendance radar, short-name subject performance visualizer, and queries |

### 🎓 Sample Student Credentials (Semester 5 IT)

Each student's default password is set to their **Date of Birth (DOB) in `DDMMYYYY` format** (numbers only, no slashes or hyphens):

| Register Number | Student Name | Date of Birth | Login Password |
| :--- | :--- | :--- | :--- |
| `911524205001` | ABICHETHRA P | 07-08-2007 | `07082007` |
| `911524205002` | ABIRAMI K | 21-04-2007 | `21042007` |
| `911524205003` | AFRIN JAISHA S | 10-05-2007 | `10052007` |
| `911524205004` | AHAMED RASIK FARITH S | 06-01-2006 | `06012006` |
| `911524205005` | AHAMED SHAKI Z | 23-04-2005 | `23042005` |
| `911524205006` | AJMAL KHAN S | 03-08-2006 | `03082006` |
| `911524205007` | AKILAN K | 16-11-2006 | `16112006` |
| `911524205008` | ALFIYA T | 11-09-2006 | `11092006` |
| `911524205009` | ANBU R | 12-05-2007 | `12052007` |
| `911524205010` | ANISHA FATHIMA M | 18-09-2007 | `18092007` |

> [!NOTE]
> Students can also log in by typing their registered full name into the username field (case-insensitive).

### 🛡️ Built-in Security Safeguards
1. **Brute-Force Account Protection**: 5 consecutive incorrect password attempts automatically locks the targeted account for 5 minutes.
2. **Anti-Enumeration Error Messaging**: Returns `"Invalid roll number, username, or password"` for all failures to prevent account harvesting.
3. **Session Inactivity Timeout**: Automatically invalidates sessions after 15 minutes of user inactivity.
4. **Data Privacy**: Password hashes, failed attempts, and raw DOB fields are strictly stripped from all outgoing student and staff API endpoints.

---

## 🚀 Core Modules & Features

### 1. HOD Administrative Panel (`/hod`)
- **Executive KPI Dashboard**: Live indicators for Total Students (62), Faculty Members, Active Subjects, Class Average Marks, and At-Risk count ($<75\%$ attendance or $<50\%$ marks).
- **Master Edit Details Hub (`/hod/edit-details`)**:
  - Unified multi-tab administrative workspace styled in Midnight Navy (`#0b1a30`).
  - **Tab 1 - Students**: Live search by Register Number or Name, filter by academic year, inline modal editing, and add student forms.
  - **Tab 2 - Faculty**: Manage designations (Assistant Professor, Associate Professor, HOD), email, contact numbers, and roles.
  - **Tab 3 - Subjects**: Maintain subject codes, semester mappings, credits, and faculty allocations.
  - **Tab 4 - Internal Marks**: 6-Subject Batch Marks Entry Modal allowing instant grading across IA-1, IA-2, and Model Exam in one dialog.
  - **Tab 5 - Attendance**: Comprehensive attendance logs with date, subject, hours, and status (Present, Absent, On Duty).
  - **Tab 6 - Timetable**: Weekly timetable schedule by day, period, room/lab, and faculty.
- **Subject Management (`/hod/subjects`)**: Real-time staff-to-subject assignment matrix.
- **Student Directory & Detailed Profiles (`/hod/students` & `/hod/student/<id>`)**: Comprehensive student dossiers featuring attendance radar, assessment timelines, and academic histories.
- **Department Reports (`/hod/reports`)**: One-click printable reports and attendance shortage alert generation.
- **CSV Data Ingest Engine (`/hod/upload`)**: Automated Pandas validation pipeline verifying duplicate roll numbers, missing marks, and attendance integrity.

### 2. Faculty / Staff Portal (`/staff`)
- **Staff Dashboard (`/staff/dashboard`)**: Summary of assigned curriculum subjects, enrolled student count, and class averages.
- **Assigned Subject Analytics (`/staff/subject-analytics`)**:
  - **Student Marks Bar Chart**: Vertical bars sorted from highest to lowest marks; missing student data rendered as distinct gray stubs at the end.
  - **6-Grade Breakdown Palette**: Unified bar and doughnut color palette:
    - **O ($\ge 90\%$)**: `#16a34a` (Green)
    - **A+ ($80-89\%$)**: `#2563eb` (Blue)
    - **A ($70-79\%$)**: `#0284c7` (Sky Blue)
    - **B+ ($60-69\%$)**: `#d97706` (Amber)
    - **B ($50-59\%$)**: `#ca8a04` (Warm Gold)
    - **RA ($< 50\%$)**: `#dc2626` (Red)
    - **No data**: `#9ca3af` (Neutral Gray)
  - **Reference Thresholds**: Dashed reference lines for **Class Average** and **Pass Mark (50%)**.
  - **Interactive Tooltip**: Hovering shows Student Name, Register Number, Marks Percentage, Letter Grade, and Class Rank.
- **Marks & Attendance Entry (`/staff/marks` & `/staff/attendance`)**: Direct entry interfaces for internal assessments and daily period attendance.
- **Timetable (`/staff/timetable`)**: Weekly teaching timetable.
- **Staff Inquiries (`/staff/queries`)**: Channel to submit requests or communicate with the HOD.

### 3. Student Academic Portal (`/student`)
- **Student Dashboard (`/student/dashboard`)**: Real-time academic KPIs (Overall Attendance %, Cumulative Marks %, Academic Standing).
- **Subject Performance Visualizer (`/student/performance`)**:
  - Visual charts showing performance across all subjects.
  - Short Subject Labels prevent text clipping on mobile and desktop viewports.
  - Hovering displays full subject title, credits, and exact scores.
- **Attendance Analytics (`/student/attendance`)**: Subject-wise percentage breakdown with visual warning indicators when attendance drops below the statutory 75% threshold.
- **Marks Transcript (`/student/marks`)**: Detailed semester-wise breakdown of Internal Assessment 1, 2, and Model Exam marks.
- **Class Timetable (`/student/timetable`)**: Weekly course schedule with room numbers and faculty details.
- **Query Submission (`/student/queries`)**: Direct grievance submission system to departmental faculty.

---

## 🏷️ Standardized Short Subject Names

To ensure charts render cleanly without cluttered x-axis labels, subjects are mapped to short names across all analytics charts:

| Semester | Full Subject Title | Code | Short Name |
| :---: | :--- | :---: | :---: |
| **Sem 5** | Cloud Computing | `CS3591` | `Cloud Comp` |
| **Sem 5** | Distributed Computing | `IT3501` | `Dist Comp` |
| **Sem 5** | Embedded Systems and IoT | `CS3551` | `IoT & Embed` |
| **Sem 5** | Foundations of Data Science | `AD3501` | `Data Sci` |
| **Sem 5** | Full Stack Web Development | `IT3511` | `Full Stack` |
| **Sem 5** | UI&UX Designing | `24CSVC08` | `UI/UX` |
| **Sem 4** | Database Management System | `CS3491` | `DBMS` |
| **Sem 4** | Computer Networks | `CS3451` | `CN` |
| **Sem 4** | Object Oriented Software Engineering | `CS3452` | `OOSE` |
| **Sem 4** | Artificial Intelligence & Machine Learning | `AI3401` | `AI & ML` |
| **Sem 4** | Environmental Science & Sustainability | `GE3451` | `EVS` |
| **Sem 4** | Web Programming | `IT3401` | `Web Prog` |
| **Sem 3** | Operating System | `CS3351` | `OS` |
| **Sem 3** | Data Structures and Algorithms | `CS3301` | `DSA` |
| **Sem 3** | Digital Principles of Computer Organisation | `CS3352` | `DPCO` |

---

## 🗄️ Database Architecture & Fallback Strategy

The application employs a resilient **Dual-Database Adapter** located in `config/database.py`:

```
                 +--------------------------------+
                 |       Flask Application        |
                 +--------------------------------+
                                 |
                     config/database.py Router
                                 |
                 +---------------+---------------+
                 |                               |
       [Primary Connection]            [Auto-Failover]
                 |                               |
                 v                               v
       Remote MySQL Cloud              Local SQLite Engine
     iriguchi.proxy.rlwy.net         student_analytics.db
     (Connection Pooled, Keepalive)    (WAL Mode, PRAGMA tuned)
```

1. **Remote Cloud MySQL**: Default primary database hosted on Railway (`30160`). Uses `PooledMySQLConnection` to recycle TCP sockets and avoid handshake overhead.
2. **Local SQLite Failover**: In the event of network disruption or cloud downtime, the system automatically falls back to `student_analytics.db` with identical schema and seeded data.
3. **Optimized SQLite PRAGMAs**: Configured with `WAL` (Write-Ahead Logging), `NORMAL` synchronous mode, `temp_store = MEMORY`, and a 256MB memory-mapped I/O cache.

---

## 🛠️ Installation & Setup Guide

### 1. Prerequisites
- **Python 3.10+** (Python 3.12, 3.13, or 3.14 recommended)
- **Git**
- **pip** package manager

### 2. Clone the Repository
```bash
git clone https://github.com/your-username/student_database_management_system.git
cd "student_database_management_system/Student-database-management-system/new try - stepupp"
```

### 3. Create & Activate a Virtual Environment
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy `.env.example` to `.env` or verify the configuration:
```ini
DB_TYPE=mysql
DB_HOST=iriguchi.proxy.rlwy.net
DB_USER=root
DB_PASSWORD=KnFpfXxCggQUXxaDvDpSfuWsDUqgMMDw
DB_NAME=railway
DB_PORT=30160
SECRET_KEY=msec_it_student_analytics_secret_key_2026
PORT=5000
DB_FALLBACK=false
```

### 6. (Optional) Ingest Students from Excel
To parse and sync the latest student roster from `student_database.xlsx` with automatic bcrypt DOB password hashing:
```bash
python import_students.py
```

### 7. Run the Application
```bash
python app.py
```
Access the application at `http://127.0.0.1:5000` in your web browser.

---

## 📁 Repository Structure

```text
student-analytics/
├── app.py                      # Application Factory & Route Registration
├── requirements.txt            # Python Dependencies Specification
├── import_students.py          # Excel Parser & Bcrypt DOB Password Ingest Tool
├── student_database.xlsx       # Master Department Student Excel Workbook
├── .env                        # Active Environment Variables
├── .env.example                # Template Environment Variables
├── Procfile                    # Cloud Deployment Specification
│
├── config/
│   └── database.py             # Dual MySQL/SQLite Connection Pool & Query Executor
│
├── database/
│   ├── seed_data.py            # Initial Schema & Database Seeder Script
│   └── railway_*.sql           # Original SQL Dumps (Students, Marks, Attendance)
│
├── routes/
│   ├── auth.py                 # RBAC Login, Logout, Session Timeout & Lockout
│   ├── hod.py                  # HOD Portal, Master Edit Hub & Reports Endpoints
│   ├── staff.py                # Staff Portal & Unified Subject Analytics Endpoints
│   ├── student.py              # Student Portal & Short-Name Performance Endpoints
│   └── csv_upload.py           # Automated Pandas CSV Ingestion Engine
│
├── services/
│   ├── analytics.py            # Pandas KPI Calculations & Dynamic Insights
│   ├── cache_service.py        # In-Memory TTL Cache for Heavy Calculations
│   ├── csv_processor.py        # CSV Schema & Data Validation Engine
│   ├── database_service.py     # SQL Aggregation Queries & Short Subject Name Map
│   └── erp_service.py          # Entity Relationship Operations & Fallbacks
│
├── static/
│   ├── css/
│   │   └── style.css           # MSEC Design System (Midnight Navy & Electric Orange)
│   ├── js/
│   │   ├── main.js             # Client Utilities, Auto-Dismiss Toasts & Global Helpers
│   │   ├── hod_charts.js       # Chart.js Renderers for HOD Department Views
│   │   └── student_charts.js   # Chart.js Visualizers for Student Performance
│   └── images/
│       ├── msec_logo.png       # Mohamed Sathak Engineering College Crest
│       └── official_banner.png # Centered NAAC/NBA Accreditation Header Banner
│
└── templates/
    ├── base.html               # Master Layout with Navigation & Institutional Banner
    ├── login.html              # Secure Authentication Portal
    ├── unauthorized.html       # 403 Forbidden Access Page
    ├── hod/                    # HOD Panel Templates (Dashboard, Edit Hub, Subjects...)
    ├── staff/                  # Staff Panel Templates (Dashboard, Subject Analytics...)
    └── student/                # Student Panel Templates (Dashboard, Performance...)
```

---

## 📄 License & Attribution

Developed for **Mohamed Sathak Engineering College (Autonomous)**, Kilakarai, Ramanathapuram District, Tamil Nadu, India.  
*Approved by AICTE, Affiliated to Anna University Chennai, NAAC A+ Accredited, NBA Accredited (CSE, IT, ECE, EEE, MECH).*

All intellectual property rights reserved &copy; 2026 Department of Information Technology, MSEC.
