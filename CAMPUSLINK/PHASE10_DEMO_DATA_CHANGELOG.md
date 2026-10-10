# Phase 10: Safe Demo Data and End-to-End Demonstration

> **Demo data is fictional and created only for demonstration/testing.**

## Management command

Run `python manage.py seed_demo_data`. The command records before/after counts, validates all deterministic identifiers before writing, and uses an atomic transaction. It creates only missing records and never updates or deletes existing records. Repeated runs report zero new rows once seeded.

There is intentionally no `--reset` option and no `clear_demo_data` command. Without a dedicated ownership table or schema marker, deletion would be too risky. Demo students use deterministic demo-only email addresses; demo jobs carry `[CAMPUSLINK_DEMO:PHASE10:JOBnn]` markers in their descriptions. The command aborts before writes if a deterministic account, student, or job identifier is occupied by a record that does not match the expected demo identity/ownership.

## Demo records and accounts

- 10 fictional students with distinct branches, academic scores, skills, and projects.
- 8 fictional jobs across 6 demo companies, with 7 OPEN and 1 CLOSED job, varied requirements and dates.
- 10 `demo_studentNN` accounts, 2 `demo_recruiterNN` accounts, and 1 `demo_tpo` account.
- Demo student users receive only the existing STUDENT group and are explicitly linked to their corresponding demo Student record.
- Demo recruiter users receive only the existing RECRUITER group and own only the demo jobs assigned to them.
- The demo TPO account receives only the existing TPO group.
- Local demo password for all newly created demo accounts: `CampusLinkDemo!2026`.
- No existing account or group membership is changed. Existing demo-identifier accounts with an unexpected identity or role cause a preflight error.

## Applications and matching

The command searches demo Student/OPEN Job pairs using the existing `evaluate_job` function and creates up to 20 eligible pairs. It does not create ineligible or closed-job applications. Existing student/job pairs are preserved and not duplicated. Statuses are assigned only as the new application row is created, cycling through the existing APPLIED, SHORTLISTED, REJECTED, OFFERED choices to make the funnel demonstrable. No match scores are stored or fabricated.

## Existing-data protection

The command does not modify or delete any existing Student, Job, Application, or unrelated User records. It does not link Rahul Kumar, assign TCS to a recruiter, or modify TCS. The command prints pre-seed and post-seed table counts and explicitly reports Rahul Kumar and TCS Software Developer as preserved.

## Demonstration flow

- Student: sign in as `demo_student01`, open the dashboard, inspect jobs/matches, apply to an eligible un-applied OPEN job, then visit My Applications.
- Recruiter: sign in as `demo_recruiter01` or `demo_recruiter02`, view owned jobs and applications, then change an application through the existing POST status workflow.
- TPO: sign in as `demo_tpo`, open the dashboard, student list, job list, application register, and placement analytics.

## Tests

- Management-command creation of users, groups, linked students, recruiter-owned demo jobs, and eligible application rows with all existing statuses.
- Repeat command execution creates no duplicates.
- Existing records remain unchanged; unrelated account membership remains unchanged.
- Conflicting deterministic identifiers abort without partial writes.
- Existing student, recruiter, TPO, analytics, Career Twin, matching, and application workflow tests remain in the project suite.
- `python manage.py check`
- `python manage.py test`
- `python manage.py makemigrations --check --dry-run`

## Known limitations

- The seed command intentionally does not clean up demo records; database administrators can identify demo students by the `demo.studentNN@campuslink.local` email pattern and jobs by their description marker, but deletion is not automated.
- Demo statuses are initialized to a varied funnel state for demonstration and can subsequently be changed by recruiters through the normal workflow.
- Applications are limited to eligible demo student/open-job pairs, so the exact number depends on the existing matching formula and seeded requirements.
- Demo credentials are for local demonstration only and must not be used in production.
