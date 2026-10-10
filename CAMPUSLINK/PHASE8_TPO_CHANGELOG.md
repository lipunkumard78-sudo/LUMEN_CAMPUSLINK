# Phase 8: TPO Placement Management Portal

## Files created

- `core/templates/core/tpo_styles.html`: shared responsive styling for TPO pages.
- `core/templates/core/tpo_students.html`: read-only student directory.
- `core/templates/core/tpo_student_detail.html`: read-only student readiness and application detail.
- `core/templates/core/tpo_jobs.html`: all-jobs directory with owner and lifecycle fields.
- `core/templates/core/tpo_job_detail.html`: read-only job record detail.
- `core/templates/core/tpo_applications.html`: read-only application register and filters.
- `PHASE8_TPO_CHANGELOG.md`: Phase 8 implementation notes.

## Files modified

- `core/views.py`: explicit TPO authorization, dashboard database statistics, and read-only student/job/application management views.
- `core/urls.py`: TPO directory and detail routes.
- `core/templates/core/tpo_dashboard.html`: placement overview counts and navigation to management pages.
- `core/tests.py`: updated TPO authorization expectation and added TPO portal coverage.

## TPO authorization

Every TPO dashboard, list, and detail view requires an authenticated user in the existing `TPO` group. Server-side views reject non-members. Staff and superuser flags do not grant TPO access, and no user is automatically assigned to a group.

## Dashboard statistics

The dashboard counts existing students, total/open/closed jobs, total applications by each existing status, students with at least one OFFERED application, and total OFFERED applications. Existing readiness calculations and skill-gap summaries remain based on current student/job records. Empty query results produce zero counts and existing empty-state messages.

## Student management

TPO users can view a directory containing name, email, branch, semester, CGPA, backlog count, skills, and derived readiness; student detail includes readiness components and existing applications. No student record is modified, and phone details are omitted.

## Job management

TPO users can view all jobs and job details, including recruiter username or “Unassigned,” status, dates, and applicant count. These pages are read-only; there is no recruiter ownership assignment or lifecycle mutation endpoint.

## Application management

The application register displays student, branch, company, job, existing explainable skill-match score, application date, and current status. Filters use database-backed choices/values for status, job, company, student, and branch. TPO views statuses but has no status modification endpoint; recruiter-owned workflow remains authoritative.

## Security rules

- TPO access is checked in every TPO view, not only in templates.
- TPO users are denied recruiter-only and student-private actions unless separately added to the corresponding group; no cross-role permissions were added.
- No role membership or recruiter ownership is assigned automatically.
- Student and recruiter view authorization behavior remains in their existing guards.

## Tests

- `python manage.py check`
- `python manage.py test`
- `python manage.py makemigrations --check --dry-run`
- Focused TPO portal tests cover anonymous/non-TPO denial, dashboard counts, student/job/application viewing, database-backed filtering, and cross-role write denial.

## Known limitations

- There is no explicit placement outcome model; placement counts reflect existing `Application.status == OFFERED` rows only.
- “Students with offers” is the distinct count of students with at least one offered application; “total offers” counts offered application rows.
- Student readiness is derived at request time from the four existing assessment scores and is not a separately persisted metric.
- Existing unassigned jobs remain unassigned; this portal does not provide ownership assignment.
