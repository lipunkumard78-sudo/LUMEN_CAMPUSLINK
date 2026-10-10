# CAMPUSLINK Final Verification

**Audit date:** 2026-09-28  
**Result:** PASS WITH DEPLOYMENT LIMITATIONS  
**Environment:** Python 3.14.2, Django 6.1.1, SQLite (`db.sqlite3`), local development settings.

## Required Checks

- `python manage.py check` — **PASS**, no issues.
- `python manage.py test` — **PASS**, 85 tests.
- `python manage.py makemigrations --check --dry-run` — **PASS**, no changes detected.
- `python manage.py showmigrations` — all Django migrations and core `0001`–`0005` applied.

## Database Snapshot

| Table | Count |
|---|---:|
| Users | 14 |
| Students | 11 |
| Jobs | 9 |
| Applications | 20 |

Demo subset: 13 demo users, 10 demo students, 8 demo jobs, 20 demo applications. Status distribution: APPLIED 5, SHORTLISTED 5, REJECTED 5, OFFERED 5.

Rahul Kumar remains ID 1 with `user=NULL` and unchanged profile values. TCS Software Developer remains ID 1 with `recruiter=NULL`, `status=OPEN`, and unchanged job values. Tests use Django’s isolated test database; live data counts remained unchanged by the audit.

## Route Verification

| Route | Anonymous | STUDENT | RECRUITER | TPO |
|---|---:|---:|---:|---:|
| `/` | 200 | 200 | 200 | 200 |
| `/accounts/login/` | 200 | 200 | 200 | 200 |
| `/student/` | 302 | 200 | 403 | 403 |
| `/student/applications/` | 302 | 200 | 403 | 403 |
| `/student/career-twin/` | 302 | 200 when linked | 403 | 403 |
| `/job/1/` | 200 | 200 with own linked profile | 200, public job only | 200, public job only |
| `/job/999/` | 404 | 404 | 404 | 404 |
| `/recruiter/` | 302 | 403 | 200 | 403 |
| `/recruiter/jobs/` | 302 | 403 | 200 | 403 |
| `/recruiter/jobs/create/` | 302 | 403 | 200 | 403 |
| `/tpo/` | 302 | 403 | 403 | 200 |
| `/tpo/students/` | 302 | 403 | 403 | 200 |
| `/tpo/jobs/` | 302 | 403 | 403 | 200 |
| `/tpo/applications/` | 302 | 403 | 403 | 200 |
| `/tpo/analytics/` | 302 | 403 | 403 | 200 |

The exact URL configuration uses `/accounts/login/` and `/accounts/logout/` rather than `/login/` and `/logout/`. Logout is POST-only (GET returns 405). Job IDs for owned recruiter pages are ownership-scoped; an unowned TCS record returns 404 to a recruiter.

Additional live object/method checks using demo accounts:

- `/recruiter/jobs/2/` — 200 for the owning demo recruiter.
- `/recruiter/jobs/2/applications/` — 200 for the owning demo recruiter.
- `/recruiter/jobs/1/` and `/recruiter/jobs/1/applications/` — 404 for that recruiter because ID 1 is unowned TCS.
- `/tpo/students/1/` and `/tpo/jobs/1/` — 200 for demo TPO.
- GET `/student/jobs/2/apply/`, `/recruiter/jobs/2/status/`, `/recruiter/applications/1/status/`, `/accounts/logout/` — 405; no state change.

## Security and Regression

- Student-private pages derive identity from the authenticated user’s linked `Student.user`; `student_id` query parameters do not select private profiles. Career Twin now uses the same linked-student guard.
- Recruiter job/applicant/status access is group- and ownership-checked server-side. TCS remains inaccessible to recruiters while unowned.
- TPO access requires the TPO group; staff/superuser alone does not grant TPO access. TPO pages remain read-only.
- CSRF middleware is enabled. Tokenless apply/status/close POSTs are rejected; mutation GETs return 405.
- Tests cover duplicate applications, allowed statuses, eligibility, role boundaries, IDOR, matching determinism, Career Twin, TPO analytics, demo seeding, and full demo flows.

Audit fixes: Career Twin now uses the linked STUDENT profile guard rather than query-string/first-record selection; recruiter job forms reject CGPA outside 0–10 and negative backlog limits. New tests also verify CSRF rejection, tokenless/GET mutation behavior, multiple-group policy, and recruiter denial for unowned TCS objects.

## Production Readiness Notes

The project intentionally defaults to local demo mode (`DEBUG=True`, console email, non-secure cookies). In that mode, `python manage.py check --deploy` reports `mail.E001` for the console backend plus Django security warnings for DEBUG, the local-only development key, HTTP redirect/cookies, and HSTS. Production mode (`DJANGO_DEBUG=false`) requires `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and an SMTP host; secure cookies and HTTPS redirect then enable. A production smoke check with temporary valid placeholders passed except for HSTS, which remains deliberately unset until HTTPS/proxy deployment is confirmed. Do not deploy the local defaults publicly.

No schema change or migration was created. No external API/dependency was introduced.
