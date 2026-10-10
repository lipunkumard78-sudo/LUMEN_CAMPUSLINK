# CAMPUSLINK Final Security and Production Readiness Audit

**Audit date:** 2026-09-28  
**Scope:** Inspection and requested verification of the existing project. No application code, schema, migrations, or live database rows were changed. This report replaces the pre-existing audit document, which described earlier work rather than recording this inspection.

## 1. Executive summary

The project is a functioning Django placement demonstration with linked student accounts, recruiter-owned jobs, TPO views and analytics, application workflows, and 85 passing tests. `manage.py check` passes, all five `core` migrations are applied, and `makemigrations --check --dry-run` reports no model changes. The observed database contains 14 users, 11 students, 9 jobs, and 20 applications.

**Overall: PASS for local demonstration; WARNING for production deployment. No CRITICAL finding identified in the reviewed routes.** Production deployment is not ready with the current default environment: `DEBUG` defaults to true, the fallback key is explicitly development-only, local SQLite is configured, and no HSTS policy or production deployment configuration is present. Demo accounts share a documented password.

## 2. Authentication audit

- **PASS** — Django built-in User, session, auth middleware, login view and password hashing are used. Login route is `/accounts/login/`; logout uses Django `LogoutView`, whose default method policy is POST-only (`core/urls.py:19-20`). The base navigation logout form is POST with a CSRF token (`core/templates/core/base.html`).
- **PASS** — Student, recruiter, and TPO views require authentication before role checks (`core/views.py:31-39, 351-377`). Anonymous requests are redirected to login.
- **PASS** — Password validators are enabled (`campuslink/settings.py:109-124`). No custom password storage is present in application models.
- **WARNING** — There is no registration or password-reset workflow. Demo accounts all use the same known local-only password, `CampusLinkDemo!2026` (`core/management/commands/seed_demo_data.py:14`, `PHASE10_DEMO_DATA_CHANGELOG.md`). Disable or rotate these accounts before public access.

## 3. Authorization audit

- **PASS** — `STUDENT` membership and an explicitly linked `Student.user` profile are both required for student private pages (`core/views.py:365-377`). Missing profiles render a linking message rather than selecting another profile.
- **PASS** — `RECRUITER` membership is checked by the recruiter guard (`core/views.py:351-359`). Recruiter lists and all job object operations use `recruiter=request.user` (`core/views.py:361-362, 424-424, 438-443, 449-449, 459-459`). Application status lookup is scoped through the owning job (`core/views.py:487-500`).
- **PASS** — TPO views are group-guarded by `TPO` (`core/views.py:31-39` and decorators on TPO views); TPO dashboards, lists, details, and analytics expose read-only operations. No TPO mutation route was found (`core/urls.py:10-17`).
- **PASS** — Staff/superuser status alone is not used as a portal-role check; Django admin remains a separate staff-protected interface. `admin.py` registers Student and Job, not Application (`core/admin.py:1-31`).
- **WARNING** — Group membership is additive. A user assigned multiple portal groups can use each corresponding portal. This is deliberate in current tests; administrators should assign only intended groups.

## 4. IDOR and security audit

- **PASS** — Student dashboards, Career Twin, application history, and application submission derive identity from the authenticated user's linked profile (`core/views.py:365-377, 507-508, 593-595, 919-923, 955-957`). No submitted `student_id` is used to select the applying student.
- **PASS** — Recruiter job detail, edit, status, and applicant routes resolve objects from recruiter-owned querysets. Application status changes are similarly ownership-scoped (`core/views.py:424-424, 438-443, 449-449, 459-459, 489-500`). A forged job/recruiter ID therefore cannot grant ownership.
- **PASS** — TPO IDs select objects only after TPO authorization. Missing objects use `get_object_or_404` (`core/views.py:278-279, 297-305`).
- **PASS** — Public job detail can show public job data but calculates personal match context only for a logged-in user with STUDENT membership and a linked profile (`core/views.py:898-915`).
- **WARNING** — `add_student` contains an unguarded record-creation view (`core/views.py:803-895`) but is not included in `core/urls.py`; it is not reachable via the configured project URL routes. Keep it unrouted or add role, form validation, and CSRF-aware workflow protections before routing it.

## 5. CSRF and HTTP method audit

- **PASS** — `CsrfViewMiddleware` is enabled (`campuslink/settings.py:65-73`). Internal mutation forms include `{% csrf_token %}`, including logout, job create/edit, job status, and application status forms. Tests verify CSRF rejection.
- **PASS** — Application creation is POST-only (`core/views.py:918-920`); recruiter job close/open and application status changes are POST-only (`core/views.py:446-448, 487-489`); logout is POST-only through Django's `LogoutView`.
- **PASS** — Job create/edit accept GET to display forms and POST to save (`core/views.py:404-406, 421-423`). No state-changing GET route was found among configured routes.
- **PASS** — Application status input is checked against declared status choices (`core/views.py:489-500`); student status is read-only. Application creation enforces eligibility/open status and uses `get_or_create` plus the database unique constraint (`core/views.py:919-950`, `core/models.py:183-215`).

## 6. Django settings audit

- **WARNING** — `DEBUG` defaults to true, and a fixed development-only `SECRET_KEY` fallback is used in DEBUG mode (`campuslink/settings.py:27-32`). Never expose this mode publicly. Production mode fails closed unless `DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS` are provided (`settings.py:28-40`).
- **PASS/WARNING** — Local allowed hosts are restricted to localhost/testserver; production uses an explicit environment allowlist (`settings.py:34-40`). Validate exact production hostnames at deployment.
- **PASS/WARNING** — CSRF and session cookies are `Secure` when `DEBUG=False`, HttpOnly is enabled for session cookies, and both use SameSite=Lax (`settings.py:42-49`). In default local DEBUG mode, secure-cookie flags are off as expected for HTTP development.
- **WARNING** — HTTPS redirect defaults on outside DEBUG (`settings.py:42-45`), but there is no HSTS setting, trusted-proxy configuration, or deployment-specific HTTPS validation. Configure these only for the actual TLS/proxy topology; run Django's deployment checks before release.
- **PASS** — Security, session, common, CSRF, authentication, messages, and clickjacking middleware are installed in the expected order (`settings.py:65-73`). Django X-Frame-Options middleware uses its default DENY policy; no override found.
- **WARNING** — SQLite is the configured database (`settings.py:98-104`), suitable for local demonstration but not a production availability/concurrency plan. `STATIC_URL` exists, but no `STATIC_ROOT`, media storage, or uploaded-file model is configured (`settings.py:138-140`; no media fields found). This is adequate for the current templates but requires static collection/serving configuration for deployment.
- **WARNING** — Production email requires SMTP configuration; local default is the console backend (`settings.py:146-169`). Email is not currently required by the demonstrated workflows.

## 7. Database and migration audit

- **PASS** — Current schema migrations are `0001` through `0005`; all are applied. The dry-run migration check reports **No changes detected**. No migration was created or applied during this audit.
- **PASS** — `Student.user` and `Job.recruiter` use `SET_NULL`; deleting an account preserves its profile/job but removes the link (`core/models.py:7-14, 96-102`). Applications protect referenced Student and Job records from deletion (`models.py:191-202`). Student/job pairs are unique (`models.py:210-215`).
- **PASS** — Application duplicate prevention is enforced in both workflow and database constraint. Existing application rows were counted without mutation.
- **WARNING** — This was a code and migration-state review, not a full forensic validation of every row's semantics or a backup/restore test. The project stores data in a local SQLite database.
- **Observed database counts:** 14 users, 11 students, 9 jobs, 20 applications. The existing verification documentation identifies 13 demo accounts plus one legacy user; audit-time inspection confirms total counts only, not credential validity for every account.

## 8. Error handling audit

- **PASS** — Invalid job/application IDs on routed object endpoints generally use `get_object_or_404`; missing job detail is tested as HTTP 404. Unauthorized group requests raise `PermissionDenied` and produce 403; anonymous requests redirect to login.
- **PASS** — Missing linked student profiles render the profile-linking message (`core/views.py:365-377`). Missing recruiter-owned jobs/applications resolve as 404 through owner-filtered querysets.
- **PASS/WARNING** — A branded 404 handler is configured (`campuslink/urls.py:9`, `core/views.py:27-28`) and covered by tests with `DEBUG=False`. Under DEBUG=True, Django intentionally displays its technical debug 404 page; this is another reason the local default must not be exposed.
- **PASS** — Invalid form values use Django form validation; job minimum CGPA is constrained to 0–10 and maximum backlogs cannot be negative (`core/forms.py:28-38`).

## 9. Demo readiness audit

- **PASS** — The seed command describes 10 fictional students, 2 recruiters, 1 TPO, 8 demo jobs, and up to 20 eligible applications. It uses an atomic transaction, preflights deterministic identifier conflicts, and uses get-or-create semantics (`core/management/commands/seed_demo_data.py:222-335, 350-405`).
- **PASS** — Current database counts are consistent with the documented demo set plus the legacy student/job and one legacy user: 14 users, 11 students, 9 jobs, 20 applications. The full test suite includes seed idempotence/preservation and end-to-end student/recruiter/TPO workflows.
- **PASS** — Existing verification documentation records successful login, student application, recruiter management, TPO review, and analytics flows. Current automated suite confirms workflow coverage.
- **WARNING** — Shared demo credentials are suitable only for an isolated local demo. No production deployment should expose these accounts unchanged.
- **WARNING** — The current local database contains 20 application rows; reports and analytics are live data-derived. Seed data is fictional and should be clearly labeled to demo users.

## 10. Findings by classification

### PASS

- Role gates, linked-profile scoping, recruiter object ownership, read-only TPO routes, CSRF middleware, POST-only mutations, duplicate-application constraint, applied migrations, clean migration dry run, branded production 404, 85 passing tests, and no live-record changes during this audit.

### WARNING

1. **Local development defaults are not production-safe:** DEBUG defaults true and a development-only fallback secret key exists. Files: `campuslink/settings.py:27-40`.
2. **Demo accounts share a known password:** file `core/management/commands/seed_demo_data.py:14`; documented in `PHASE10_DEMO_DATA_CHANGELOG.md`.
3. **Production deployment configuration remains incomplete:** no HSTS/proxy policy, SQLite backend, or static collection root is configured. Files: `campuslink/settings.py:42-49, 98-104, 138-140`.
4. **Unrouted legacy student-creation view:** `core/views.py:803-895`; absent from `core/urls.py`. It is currently not an externally reachable route.
5. **Role groups are additive:** multiple memberships grant multiple role portals. Review group assignments during account administration.

### CRITICAL

- **None identified in the configured application routes during this audit.** This does not establish production readiness or replace deployment/environment review.

## 11. Recommended fixes

No fixes were implemented, as requested. Before production deployment:

1. Set `DJANGO_DEBUG=false`; provide a unique high-entropy `DJANGO_SECRET_KEY` through secret management and an exact `DJANGO_ALLOWED_HOSTS` list.
2. Disable or rotate all shared demo credentials and demo accounts; use unique credentials and least-privilege role assignments.
3. Select and configure a production database, backups/restore monitoring, static asset collection and serving, HTTPS termination, proxy handling, and a tested HSTS policy.
4. Run `manage.py check --deploy` in the final production-like environment and resolve or formally accept each finding.
5. Keep `add_student` unrouted unless it is replaced with a guarded, validated workflow.
6. Add operational controls appropriate to the actual deployment, including monitoring, backup restore drills, and login abuse/rate limiting.

## 12. Final production-readiness checklist

- [ ] `DEBUG=False`, production secret stored outside source, and exact `ALLOWED_HOSTS` configured.
- [ ] HTTPS redirect, secure cookies, proxy configuration, and HSTS verified against the real deployment path.
- [ ] Shared demo accounts disabled or rotated; role assignments reviewed.
- [ ] Production database, backups, restore test, monitoring, and retention plan configured.
- [ ] Static files collected and served; media storage configured if uploads are later introduced.
- [ ] `manage.py check --deploy` reviewed in production-like settings.
- [x] Application checks pass; tests pass; migrations are applied and migration dry run is clean.
- [x] No database records were changed by this audit.

## Verification results

- **Tests:** 85 passed; `manage.py test` returned OK (83.607 seconds).
- **System check:** `manage.py check` — no issues (0 silenced).
- **Migration status:** core `0001`–`0005` all marked applied.
- **Migrations clean:** yes; `makemigrations --check --dry-run` reported no changes detected.
- **Live database counts:** 14 users, 11 students, 9 jobs, 20 applications.
- **Database record changes:** none. Tests used Django's isolated in-memory test database; read-only count/check commands did not modify live rows. No migration or seed command was run.
