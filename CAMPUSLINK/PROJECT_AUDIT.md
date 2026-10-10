# CAMPUSLINK PROJECT AUDIT & ARCHITECTURAL BLUEPRINT
**Platform:** CAMPUSLINK 360 — *"From Student to Career"*  
**Author:** Lead Software Architect  
**Date:** September 23, 2026  
**Target:** BPUT Hackathon Platform Transformation  
**Status:** Historical initial-state blueprint; superseded by Phases 1–12. See [FINAL_VERIFICATION.md](FINAL_VERIFICATION.md), [FINAL_SECURITY_AUDIT.md](FINAL_SECURITY_AUDIT.md), and [FINAL_PROJECT_REPORT.md](FINAL_PROJECT_REPORT.md) for the current implementation and audit findings.  

---

## 1. Executive Summary

A comprehensive, non-destructive audit of the existing **CAMPUSLINK** codebase was conducted. The application is an early-stage Django project designed to assess student readiness and perform basic job compatibility checks.

The core algorithm for skill matching, CGPA/backlog eligibility evaluation, and composite readiness scoring is functional and logically sound. However, the application currently lacks authentication flows, role segregation, multi-user association, interactive student dashboards, recruiter portals, centralized layout templates, and production dependency tracking.

This document details the complete current state, verified issues, preserved assets, refactoring targets, and the architectural plan to elevate CAMPUSLINK into **CAMPUSLINK 360**.

---

## 2. Current Architecture Overview

```
CAMPUSLINK Repository Root
│
├── manage.py                          # Django management script
├── db.sqlite3                         # SQLite database (147 KB, active data present)
│
├── campuslink/                        # Project configuration package
│   ├── __init__.py
│   ├── asgi.py                        # ASGI entrypoint
│   ├── wsgi.py                        # WSGI entrypoint
│   ├── settings.py                    # Django configuration (Django 6.1.1 on Python 3.14.2)
│   └── urls.py                        # Project root URL routing (monolithic, no app include)
│
├── core/                              # Single active Django application
│   ├── __init__.py
│   ├── admin.py                       # ModelAdmin registrations for Student & Job
│   ├── apps.py                        # AppConfig ('core')
│   ├── models.py                      # Student & Job models
│   ├── views.py                       # home, student_dashboard, add_student, job_match
│   ├── tests.py                       # Empty test placeholder
│   │
│   ├── migrations/                    # 3 schema migrations applied
│   │   ├── 0001_initial.py            # Created Student table
│   │   ├── 0002_student_*.py          # Added readiness score columns to Student
│   │   └── 0003_job.py                # Created Job table
│   │
│   └── templates/core/                # Application templates (standalone HTML, no base inheritance)
│       ├── home.html                  # Landing page with static hero & mock metrics
│       ├── student_dashboard.html     # Dashboard template with missing context variables
│       └── job_match.html             # Fully functional job matching & eligibility report
│
└── venv/                              # Python 3.14.2 virtual environment
```

### Environment & Technology Stack
- **Python Version:** `3.14.2` (64-bit AMD64)
- **Django Version:** `6.1.1`
- **Database Engine:** `django.db.backends.sqlite3` (`db.sqlite3`)
- **Key Installed Packages:** `Django==6.1.1`, `asgiref==3.12.1`, `sqlparse==0.6.0`, `tzdata==2026.4`
- **Requirements File:** **Missing** (no `requirements.txt` present in repository)
- **Static Asset Pipeline:** No static directories configured; CSS is 100% inline `<style>` tags.

---

## 3. Existing Django Apps & Component Analysis

### Application: `core`
The project currently has only **one custom Django app** (`core`).

#### Model Layer (`core/models.py`)
1. **`Student` Model:**
   - **Fields:**
     - `name` (`CharField(max_length=100)`)
     - `email` (`EmailField(unique=True)`)
     - `phone` (`CharField(max_length=15)`)
     - `branch` (`CharField(max_length=100)`)
     - `semester` (`IntegerField()`)
     - `cgpa` (`DecimalField(max_digits=4, decimal_places=2)`)
     - `backlogs` (`IntegerField(default=0)`)
     - `technical_score` (`IntegerField(default=0)`)
     - `aptitude_score` (`IntegerField(default=0)`)
     - `communication_score` (`IntegerField(default=0)`)
     - `interview_score` (`IntegerField(default=0)`)
     - `skills` (`TextField(help_text="Enter skills separated by commas")`)
     - `projects` (`TextField(blank=True)`)
     - `certifications` (`TextField(blank=True)`)
   - **Relationships:** None. Has no link to Django's `auth.User`.
   - **Method:** `__str__` returns `self.name`.

2. **`Job` Model:**
   - **Fields:**
     - `company_name` (`CharField(max_length=100)`)
     - `job_title` (`CharField(max_length=100)`)
     - `description` (`TextField(blank=True)`)
     - `required_skills` (`TextField(help_text="Enter required skills separated by commas")`)
     - `minimum_cgpa` (`DecimalField(max_digits=4, decimal_places=2, default=0)`)
     - `maximum_backlogs` (`IntegerField(default=0)`)
     - `location` (`CharField(max_length=100, blank=True)`)
     - `package` (`CharField(max_length=100, blank=True)`)
     - `created_at` (`DateTimeField(auto_now_add=True)`)
   - **Relationships:** None. Standalone job posting entity.
   - **Method:** `__str__` returns `f"{self.company_name} - {self.job_title}"`.

#### View Layer (`core/views.py`)
- **`home(request)`:** Serves static landing page `core/home.html`.
- **`student_dashboard(request)`:** Queries `Student.objects.all()`, takes `student = students.first()`, renders `core/student_dashboard.html`.
- **`add_student(request)`:** Handles POST to create a `Student` and redirect to dashboard, or GET to render `core/add_student.html`. **(Note: Unrouted and template missing)**.
- **`job_match(request, job_id)`:** Compares `Student.objects.first()` with `Job(id=job_id)`. Computes skills intersection, match percentage, CGPA eligibility, backlog eligibility, overall qualification, and average readiness score. Renders `core/job_match.html`.

#### Admin Configuration (`core/admin.py`)
- `StudentAdmin`: Configured with list displays for academic & assessment scores (`name`, `branch`, `cgpa`, `backlogs`, `technical_score`, `aptitude_score`, `communication_score`, `interview_score`).
- `JobAdmin`: Configured with list displays for job parameters (`company_name`, `job_title`, `minimum_cgpa`, `maximum_backlogs`, `location`, `package`).

---

## 4. Database Entities & Existing Data State

Direct query inspection of `db.sqlite3` revealed:
- **Total Tables:** 13 tables (11 standard Django auth/session/admin tables + 2 app tables: `core_student`, `core_job`).
- **`core_student` Table:** 1 verified active record:
  - **ID:** 1
  - **Name:** Rahul Kumar
  - **Email:** `rahul@test.com`
  - **Phone:** `9876543210`
  - **Branch:** `MCA`
  - **Semester:** `1`
  - **CGPA:** `8.20`
  - **Backlogs:** `0`
  - **Skills:** `"Python, SQL, Django, HTML, CSS, C"`
  - **Projects:** `"Smart Clinic Management System"`
  - **Certifications:** `"Python Programming Certificate"`
  - **Scores:** Technical: 75 | Aptitude: 72 | Communication: 68 | Interview: 70
- **`core_job` Table:** 1 verified active record:
  - **ID:** 1
  - **Company:** TCS
  - **Job Title:** Software Developer
  - **Required Skills:** `"Python, SQL, Data Structures, Algorithms, Git, OOPS"`
  - **Minimum CGPA:** `6.00`
  - **Maximum Backlogs:** `0`
  - **Location:** Bhubaneswar
  - **Package:** 5 LPA
- **`auth_user` Table:** 1 superuser:
  - **Username:** `protonova`
  - **Email:** `lipunkumard78@gmail.com`
  - **Role:** Superuser / Staff

---

## 5. URL Map & Routing Analysis

| URL Pattern | View Function | URL Name | HTTP Methods | Status / Issues |
| :--- | :--- | :--- | :--- | :--- |
| `admin/` | `django.contrib.admin.site.urls` | N/A | GET, POST | **Working** (Superuser `protonova` can log in) |
| `/` | `core.views.home` | `home` | GET | **Working** (Static landing page) |
| `student/` | `core.views.student_dashboard` | `student_dashboard` | GET | **Working with Missing Context** (Renders `%` for readiness) |
| `job/<int:job_id>/` | `core.views.job_match` | `job_match` | GET | **Working** (Accurately calculates TCS match for Rahul Kumar) |
| N/A | `core.views.add_student` | None | GET, POST | **Broken/Unrouted** (Not in `urls.py`, missing template) |

*Notice: Routing is defined solely inside `campuslink/urls.py`. `core` does not have its own `urls.py` file.*

---

## 6. Template Map & UI Architecture

| Template Path | Purpose | Dependencies / Context Received | Missing Context / Defects |
| :--- | :--- | :--- | :--- |
| `core/templates/core/home.html` | Hero landing page | None | Buttons ("Login", "Get Started", "Explore") have no URLs or actions. All metrics are hardcoded HTML. |
| `core/templates/core/student_dashboard.html` | Student Overview | Receives `student`, `students` | **Missing:** `readiness`, `readiness_level`, `skill_match`, `matched_skills`, `missing_skills`. Result: renders blank `%` and default empty lists. |
| `core/templates/core/job_match.html` | Match & Eligibility Report | Receives `student`, `job`, `matched_skills`, `missing_skills`, `skill_match`, `cgpa_eligible`, `backlog_eligible`, `eligible`, `readiness_score` | Fully functional, but hardcoded to single student. |
| `core/templates/core/add_student.html` | Form to create a student | Referenced by `views.add_student` | **File does not exist** on disk. |

*Styling Analysis:*
- No CSS framework or shared stylesheet is linked.
- Each template has an isolated, redundant `<style>` block in `<head>`.
- Color theme in place: Deep Navy (`#0b1f3a`, `#173f5f`, `#1f4e79`) paired with Teal/Emerald accents (`#20c7b5`, `#12a99a`, `#2563eb`).

---

## 7. Authentication & Role-Based Access Flow

1. **Current State:**
   - Standard Django auth is installed (`django.contrib.auth`), but **no user-facing authentication flow exists**.
   - There are no login, logout, registration, or password reset views/templates.
   - The `Student` model stores contact details but has no foreign key or `OneToOneField` linking to `auth.models.User`.
   - The views have zero access restrictions: anyone can navigate to `/student/` and `/job/1/` without logging in.
2. **Role Model:**
   - **No role distinction exists** in the database or views.
   - There is no Recruiter model, no Training & Placement Officer (TPO) model, and no Student account linkage.

---

## 8. Detailed Analysis of Features

### 8.1 Job Matching Engine (`core/views.py:job_match`)
- **How it works:**
  - Tokenizes comma-separated skills: `[s.strip().lower() for s in skills.split(',') if s.strip()]`.
  - Computes `matched_skills = [s for s in required if s in student_skills]`.
  - Computes `missing_skills = [s for s in required if s not in student_skills]`.
  - Computes percentage: `round((len(matched_skills) / len(required_skills)) * 100)`.
  - Checks eligibility:
    - `cgpa_eligible = student.cgpa >= job.minimum_cgpa`
    - `backlog_eligible = student.backlogs <= job.maximum_backlogs`
    - `eligible = cgpa_eligible and backlog_eligible and (skill_match >= 50)`
  - Calculates readiness: `round((tech + apt + comm + interview) / 4)`.
- **Verdict:** Highly effective, transparent, deterministic rule-based matching engine. **Must be preserved and extended.**

### 8.2 Student Dashboard (`core/views.py:student_dashboard`)
- **How it works:**
  - Fetches `Student.objects.first()`.
  - Context passed: `{"student": student, "students": students}`.
- **Defects verified by execution:**
  - `student_dashboard.html` expects `{{ readiness }}%`, `{{ readiness_level }}`, `{{ skill_match }}%`, `matched_skills`, and `missing_skills`.
  - Because these are never computed or passed from the view, the dashboard displays `%` with no number, no readiness level badge, `% Skill Match`, and "No matching skills found" for the target role.
- **Verdict:** The view is half-finished. The template already anticipated the readiness and skill-match features, but the view logic was never wired.

### 8.3 Student Registration (`core/views.py:add_student`)
- **How it works:**
  - Contains form handling for 14 student fields.
  - Redirects to `student_dashboard` on POST.
- **Defects verified:**
  - Completely absent from `campuslink/urls.py`.
  - Missing template `core/add_student.html`.
- **Verdict:** Broken / dormant code.

### 8.4 Recruiter Functionality
- **Current State:**
  - Zero recruiter-facing views or dashboards.
  - Jobs can only be created via the Django Admin interface (`/admin/core/job/`).
  - No mechanism for recruiters to view applicants, post drives, or download candidate shortlists.

---

## 9. Problems & Vulnerabilities Discovered

1. **Hardcoded Single-Student Constraint:**
   - Both `student_dashboard` and `job_match` use `Student.objects.first()`. If 50 students are added to the database, only the first student can ever be inspected.
2. **Missing Template & Broken Route for `add_student`:**
   - `core/views.py` contains `add_student()`, but it has no route and its template does not exist.
3. **Template Context Discrepancy in `student_dashboard`:**
   - The UI template includes skill gap analysis and readiness score meters, but the view provides no values, leaving ugly blank percentage signs (`%`).
4. **Zero Authentication & Security:**
   - `SECRET_KEY` is committed in plain text.
   - `ALLOWED_HOSTS = []` triggers 400 Bad Request when running in certain environments or when running tests.
   - No login or permission gates protecting student personal data, phone numbers, or academic records.
5. **No Static Files Architecture:**
   - All styles are repeated inline across HTML files; no centralized `base.html` layout, stylesheet, or JavaScript files.
6. **No Dependencies Manifest:**
   - Lack of `requirements.txt` threatens portability across development and deployment environments.
7. **Comma-Separated Text for Skills:**
   - Storing skills as flat text strings (`"Python, SQL, Django"`) limits advanced querying, skill normalization (e.g. `node.js` vs `nodejs`), taxonomy matching, and indexing.
8. **No Job Application Pipeline:**
   - No table or mechanism connects a `Student` applying to a `Job`. The system can match, but cannot track application states (Applied, Shortlisted, Interview Scheduled, Selected, Rejected).

---

## 10. Code Preservation vs. Refactoring Strategy

### Features to PRESERVE Intact
- **Eligibility & Skill Compatibility Logic:** The math and logic in `core/views.py:job_match` (skill overlap percentage, CGPA cutoff, backlog filter, composite eligibility rule, readiness score average) is solid and validated. We will preserve this mathematical foundation and package it into a reusable service module (`MatchingService`).
- **Existing Database Records:** Student `Rahul Kumar` and Job `TCS Software Developer` in `db.sqlite3` must remain intact and functional.
- **Visual Design Identity:** The clean navy-and-teal palette (`#0b1f3a`, `#173f5f`, `#20c7b5`) and card-based UX from `home.html` and `job_match.html` will be preserved and formalized into a master template `base.html`.

### Features to REFACTOR & ENHANCE
- **Student Dashboard View (`student_dashboard`):** Refactor to dynamically calculate the student's 360° readiness score and compare their skills with available jobs or default benchmark roles so the template renders complete, dynamic metrics.
- **Student Model Linkage:** Connect `Student` to Django's `User` via `OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)` to enable secure login without breaking existing database rows.
- **`add_student` Workflow:** Connect to an actual form and template or integrate into student profile onboarding.
- **URL Configuration:** Decouple URL patterns by creating `core/urls.py` and referencing it with `include('core.urls')` in `campuslink/urls.py`.

---

## 11. Proposed Architecture: CAMPUSLINK 360

```
+---------------------------------------------------------------------------------------+
|                                    CAMPUSLINK 360                                     |
|                           "From Student to Career"                                    |
+---------------------------------------------------------------------------------------+
|                                                                                       |
|   [ Public Portal ]                                                                   |
|   ├── Landing Page (Dynamic metrics, live drive ticker, feature showcase)             |
|   ├── Unified Authentication (Login, Role-based Registration, Logout)                 |
|                                                                                       |
|   [ Role 1: Student 360 ]                                                             |
|   ├── 360° Readiness Index (Academics, Tech, Aptitude, Comm, Interview)               |
|   ├── Skill Gap Visualizer (Role vs. Student Profile, missing skill recommendations)  |
|   ├── Job Exploration & Smart Fit Badge (Live match % with eligible jobs)             |
|   ├── One-Click Application & Application Status Tracker                              |
|                                                                                       |
|   [ Role 2: Recruiter 360 ]                                                           |
|   ├── Recruiter Profile & Company Branding                                            |
|   ├── Job & Placement Drive Posting (Skill requirements, CGPA & backlog criteria)     |
|   ├── Automated Candidate Ranking Engine (Instant pool matching & match score sorting)|
|   ├── Candidate Shortlist & Status Manager (Applied -> Shortlisted -> Hired)          |
|                                                                                       |
|   [ Role 3: TPO 360 (Training & Placement Cell) ]                                     |
|   ├── College Placement Intelligence Dashboard                                        |
|   ├── Branch-wise & Batch-wise Readiness Distribution (BPUT MCA, B.Tech, etc.)       |
|   ├── Drive Conflict & Schedule Planner                                               |
|   ├── Unplaced Student Action List (Targeted interventions for high skill gap)        |
|                                                                                       |
+---------------------------------------------------------------------------------------+
|                            Core Intelligence Services                                 |
|   ├── MatchingService (Normalized skill matching, multi-criteria eligibility)        |
|   ├── ReadinessEngine (Weighted 360 readiness scoring)                                |
|   ├── PlacementAnalytics (Aggregation & insight generation)                           |
+---------------------------------------------------------------------------------------+
```

### Proposed Data Models (Additive & Non-Destructive)
1. **`User` (Django `auth.User`) + `UserProfile` / Roles:**
   - Roles: `STUDENT`, `RECRUITER`, `TPO_ADMIN`.
2. **`Student` (Preserved & Extended):**
   - Retain all existing fields (`technical_score`, `aptitude_score`, `communication_score`, `interview_score`, etc.).
   - Add `user = OneToOneField(User, null=True, blank=True)`.
   - Add `college_name` (Default: "BPUT / Affiliated Institution").
   - Add `resume` file field (optional).
3. **`Job` (Preserved & Extended):**
   - Retain all existing fields (`company_name`, `job_title`, `required_skills`, `minimum_cgpa`, `maximum_backlogs`, etc.).
   - Add `posted_by = ForeignKey(User, null=True, blank=True)`.
   - Add `deadline = DateField(null=True, blank=True)`.
   - Add `drive_date = DateField(null=True, blank=True)` for schedule planning.
   - Add `status = CharField(choices=['OPEN', 'CLOSED', 'SCHEDULED'])`.
4. **`Application` (New Model):**
   - `student = ForeignKey(Student, on_delete=models.CASCADE)`
   - `job = ForeignKey(Job, on_delete=models.CASCADE)`
   - `applied_at = DateTimeField(auto_now_add=True)`
   - `match_score = IntegerField(default=0)`
   - `status = CharField(choices=['APPLIED', 'SHORTLISTED', 'REJECTED', 'OFFERED'])`

---

## 12. Verification & Health Check Results

- **Django Check:** `python manage.py check` -> **Passed** (0 errors, 0 warnings).
- **Migration Status:** All migrations (`0001`, `0002`, `0003`) are applied.
- **Endpoint Tests:**
  - `GET /` -> Status `200 OK`
  - `GET /student/` -> Status `200 OK` (displays profile, but missing score context)
  - `GET /job/1/` -> Status `200 OK` (accurately matches Rahul Kumar with TCS)
  - `GET /job/999/` -> Status `404 Not Found` (clean 404 handling)
  - `GET /admin/login/` -> Status `200 OK`

---

## 13. Immediate Next Steps (Pending Approval)

1. Review and approve `PROJECT_AUDIT.md`.
2. Create `requirements.txt` to lock project dependencies.
3. Configure `ALLOWED_HOSTS` and modular routing (`core/urls.py`).
4. Implement master template layout (`core/templates/core/base.html`) preserving existing aesthetics.
5. Fix the missing context logic in `student_dashboard` so that Rahul Kumar's readiness index and skill gaps display dynamically.
6. Build out the CAMPUSLINK 360 multi-role architecture in phases.
