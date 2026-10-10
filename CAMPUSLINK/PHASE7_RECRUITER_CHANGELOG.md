# Phase 7: Recruiter Portal

## Files created

- `core/forms.py`: recruiter job form using the existing `Job` model.
- `core/templates/core/recruiter_styles.html`: shared recruiter portal styles.
- `core/templates/core/recruiter_dashboard.html`: scoped recruiter statistics and recent jobs.
- `core/templates/core/recruiter_jobs.html`: owned job list and lifecycle actions.
- `core/templates/core/recruiter_job_form.html`: create/edit job form.
- `core/templates/core/recruiter_job_detail.html`: owned job details and actions.
- `core/templates/core/recruiter_applications.html`: applicants and status controls.
- `core/templates/core/login.html`: Django authentication login page.

## Files modified

- `core/views.py`: recruiter authorization, dashboard, job CRUD/display, job lifecycle, applicant listing, and status update views.
- `core/urls.py`: recruiter routes and Django login/logout routes.
- `core/templates/core/base.html`: recruiter portal and authentication navigation.
- `core/tests.py`: recruiter access, ownership, lifecycle, privacy, validation, empty-state, and existing-page regression tests.

## Authorization and ownership

- Recruiter routes require an authenticated account in the existing `RECRUITER` auth group.
- Staff and superuser flags do not grant recruiter access.
- No user is automatically added to the group.
- Job queries are scoped to `recruiter=request.user`; job detail, edit, close/open, and applicants use those scoped queries.
- Application status updates filter through `job__recruiter=request.user` and accept only the existing APPLIED, SHORTLISTED, REJECTED, and OFFERED choices.
- Job creation forces `recruiter=request.user` and status OPEN on the server, ignoring submitted ownership and submitted status.

## Workflow

- Recruiters can create, list, view, edit, close, and reopen their jobs.
- Applicants are loaded only for the owned job and show student name, branch, CGPA, application date, current status, and the existing `evaluate_job` skill-match percentage.
- Dashboard totals use database queries over the recruiter's jobs and their applications.
- Empty job and applicant states are rendered without errors.

## Tests performed

- `python manage.py check`
- `python manage.py test core.tests.RecruiterPortalTests`
- `python manage.py test`
- `python manage.py makemigrations --check --dry-run`

## Known limitations

- `Student` has no college field, so the applicant page displays “Not recorded” for college.
- The existing project has no student-facing application submission endpoint; this phase leaves that workflow and the `Application` model unchanged. Tests cover the existing model relationship and student-facing dashboard, Career Twin, and job matching pages.
- Existing unowned jobs, including TCS Software Developer, do not appear in a recruiter portal until an administrator explicitly assigns ownership.
- Recruiter group membership and account creation remain administrator-managed; no registration or automatic role assignment was added.
