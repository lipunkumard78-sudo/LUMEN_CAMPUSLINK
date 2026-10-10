# Student Application Workflow

## Authentication requirements

The student dashboard, application history, and application submission require an authenticated account in the existing Django `STUDENT` group. Student-private views resolve the profile only through `Student.user == request.user`. A missing linked profile receives a clear linking message; no first-record, username, email, URL, or query-string fallback is used for these actions.

Job detail remains public for job information. Personal match, readiness, and eligibility data are shown only when the requester is in `STUDENT` and has a linked profile. For an authenticated STUDENT, query-string `student_id` values are ignored.

## Student profile linking

An administrator must explicitly link the existing `Student` row to the user's `Student.user` one-to-one relation and add the user to the `STUDENT` group. Existing students are not automatically linked.

## Application creation

The job detail page submits to `/student/jobs/<job_id>/apply/` using POST and CSRF protection. The server obtains the student from the authenticated user's linked profile and the job from the URL. Submitted student identifiers are ignored.

Before creation, the view checks the existing `evaluate_job` result, requires job status OPEN, and checks for an existing application. It creates an `Application` with status APPLIED. `get_or_create` and the existing unique student/job constraint prevent duplicates.

Ineligible students receive the matching criteria that were not met. Closed jobs and prior applications receive clear feedback and no additional row is created.

## Application privacy and status

`/student/applications/` filters exclusively by the authenticated user's linked Student profile. It displays company, job, application date, match score, status, and deadline. Status is displayed without student-side controls. Status changes remain available only through the existing recruiter-group, job-ownership-protected POST route.

## Tests performed

- Student group and linked-profile requirements, including anonymous, non-student, and unlinked users.
- Dashboard and job detail ignore forged `student_id` values for STUDENT users.
- Eligible application, ineligible application, closed job, duplicate prevention, and server-derived student identity.
- Profile-scoped application history, deadline display, and read-only status.
- Recruiter application access and status workflow regression tests.
- Existing matching, Career Twin, job 404, and full project test coverage.
- `python manage.py check`
- `python manage.py test`
- `python manage.py makemigrations --check --dry-run`
