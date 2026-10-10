# CAMPUSLINK Final Project Report

**Project:** CAMPUSLINK — Intelligent Campus Placement Platform  
**Audit date:** 2026-09-28  
**Status:** Demonstration-ready with documented production limitations.

## 1. Project Title

CAMPUSLINK — an explainable placement workflow platform for students, recruiters, and Training & Placement Officers (TPOs).

## 2. Problem Statement

Campus placement activity spans student readiness, job requirements, applications, recruiter review, and placement-cell oversight. These records and decisions need a shared application that makes eligibility and skill matching understandable while restricting private workflows by role.

## 3. Objectives

- Present student readiness and job opportunities from stored records.
- Explain job compatibility using exact recorded skills and academic cutoffs.
- Support authenticated student applications and private application history.
- Let recruiters manage only their own jobs and applicants.
- Give TPO users read-only placement management and descriptive analytics.
- Preserve real data and use clearly identifiable fictional demo records.

## 4. Existing System and Problem

The initial application was a single Django app with Student/Job records and a static dashboard. It lacked linked user profiles, applications, recruiter ownership, and placement outcomes. Those capabilities have since been added incrementally while retaining Rahul Kumar and TCS Software Developer records.

## 5. Proposed Solution

CAMPUSLINK uses Django’s built-in User, Group, session, and CSRF systems; existing Student, Job, and Application models; server-side ownership checks; and a shared deterministic matcher. Presentation flows are role-specific, and TPO analytics are calculated from current database rows rather than fixture values.

## 6. Technology Stack

- Python 3.14.2
- Django 6.1.1
- SQLite for local demonstration
- Django templates and local inline/partial CSS
- Django auth groups for STUDENT, RECRUITER, and TPO

`requirements.txt` contains Django and its standard dependencies. No external AI/API, charting, or frontend framework dependency is used.

## 7. System Architecture

One Django project (`campuslink`) hosts one application (`core`). `core.models` owns Student, Job, and Application data; `core.views` provides role-protected workflows; `core.matching` contains shared deterministic matching; Django templates render the role-specific interfaces; SQLite stores live and demo records.

## 8. Main Modules

- Public home and Django login/logout.
- Student dashboard/job discovery, job match details, application submission/history, and Career Twin.
- Recruiter dashboard, owned job CRUD/lifecycle, applicants, and status management.
- TPO dashboard, student/job/application read-only pages, and placement analytics.
- Repeatable `seed_demo_data` management command.

## 9. Student Workflow

Student-only pages require authentication, STUDENT group membership, and an explicitly linked `Student.user`. Students discover jobs at `/student/`, inspect `/job/<job_id>/`, apply through POST only when eligible for an OPEN job, and review their own applications at `/student/applications/`. Application status is read-only to students.

## 10. Recruiter Workflow

Recruiter pages require authentication and RECRUITER group membership. Job creation assigns ownership server-side; listing, editing, status changes, and applicants filter by `recruiter=request.user`. Recruiter status changes use POST and the existing status choices. Unowned TCS is not visible or writable through recruiter-owned object routes.

## 11. TPO Workflow

Every TPO page requires authentication and TPO group membership; staff/superuser alone is insufficient. TPO can view students, jobs, applications, and analytics but has no recruiter ownership or application-status mutation route.

## 12. Explainable Job Matching

`core.matching.parse_skills`, `compare_skills`, and `evaluate_job` trim and case-fold exact skill names, deduplicate case-only repeats, and calculate skill overlap, CGPA/backlog eligibility, explanation factors, strengths, and improvement steps. There is no synonym inference. The eligibility threshold remains at least 50% exact skill coverage plus academic cutoffs.

## 13. Career Twin

Career Twin displays the linked student’s four assessment scores, readiness, profile skills, missing/matched job requirements, role analyses, and rule-based recommendations. Readiness remains the rounded unweighted mean of technical, aptitude, communication, and interview scores. Private access now uses the same linked STUDENT profile guard; query IDs cannot select another profile.

## 14. Application Workflow

The existing Application model links a Student and Job, stores `applied_at`, and uses APPLIED, SHORTLISTED, REJECTED, OFFERED. Student submissions use the linked profile, existing eligibility logic, OPEN status, `get_or_create`, and the database uniqueness constraint. Recruiters can update status only for applications under their owned jobs; TPO can view statuses read-only.

## 15. Analytics

TPO analytics at `/tpo/analytics/` derives student, job, application funnel, offer, skill demand/gap, match, readiness, branch, and company summaries from the existing models. Offered application rows are distinguished from distinct students with offers. Small datasets use explicit insufficient-data states. No fictional placement statistics are generated.

## 16. Database Design

- **Student:** nullable one-to-one User link; identity/contact, branch/semester, CGPA/backlogs, four assessment scores, skills/projects/certifications.
- **Job:** nullable recruiter FK; company/role, requirements, CGPA/backlog cutoffs, location/package, OPEN/CLOSED, optional deadline/drive date, creation date.
- **Application:** Student and Job FKs, application timestamp, existing status choices, unique Student/Job constraint.

Migrations `0001`–`0005` are applied. No Phase 11/12 schema changes are pending.

## 17. Authentication and Authorization

Django User and Groups are used; no parallel User or role model exists. Student identity derives from `Student.user`; recruiter object access is owner-filtered; TPO pages are group-protected. CSRF middleware is enabled, mutations use POST, and secure role boundaries are covered by tests.

## 18. Testing

- `python manage.py check`: PASS.
- `python manage.py test`: **85 tests PASS**.
- `python manage.py makemigrations --check --dry-run`: no changes detected.
- Tests include matching determinism, student privacy/apply/history, recruiter ownership/POST status, TPO authorization/read-only behavior/analytics, repeatable demo seeding, and CSRF/GET-mutation checks.

## 19. Demo Data

Current live database: 14 users, 11 students, 9 jobs, 20 applications. The demo subset contains 13 demo accounts, 10 students, 8 jobs, and 20 applications with five rows in each existing status. `seed_demo_data` is idempotent and creates eligible demo applications. No cleanup/reset command is provided. Demo data is fictional and intended for local demonstration/testing only.

## 20. Known Limitations

- SQLite and DEBUG-mode defaults are for local demonstration, not public production deployment.
- Production requires environment-provided secret key, host allowlist, HTTPS/email configuration; HSTS must be selected only after deployment topology is confirmed.
- There is no password reset/registration or production email flow.
- Student has no college field, so recruiter applicant views show “Not recorded.”
- Analytics are current-record descriptive snapshots, not historical or predictive outcomes.
- No historical placement-outcome model, rate limiting, backup/monitoring, or production deployment pipeline is included.

## 21. Future Enhancements

Potential later work includes administrator-managed account linking/onboarding, transactional email configured for a real provider, database-backed historical reporting, and production operations hardening. These are not implemented or claimed as current capabilities.
