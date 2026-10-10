# CAMPUSLINK Final Demo Check — Phase 13

**Date:** 2026-09-28  
**Result:** PASS — existing student, recruiter, and TPO workflow verified. No demo-blocking bug found.

## Exact demo steps

The local demo accounts share the password `CampusLinkDemo!2026` (from `PHASE10_DEMO_DATA_CHANGELOG.md`). Use this only with the isolated local demo.

1. Start the existing Django app from the `CAMPUSLINK` directory:

   ```powershell
   .\venv\Scripts\python.exe manage.py runserver
   ```

2. Open `http://127.0.0.1:8000/accounts/login/` and sign in as `demo_student10`.
3. Open the student dashboard at `http://127.0.0.1:8000/student/`. Choose the eligible OPEN listing **Demo Job 07 - Systems Developer** (job ID 8), then open its details at `http://127.0.0.1:8000/job/8/` and submit the application.
4. Confirm the application appears in My Applications at `http://127.0.0.1:8000/student/applications/` with status **Applied**.
5. Log out using the POST logout button. Sign in as `demo_recruiter01` with the same local demo password.
6. Open `http://127.0.0.1:8000/recruiter/jobs/8/applications/`. Review the new applicant and change the status using the page's status form (for example, to **Shortlisted**). Confirm the updated status appears.
7. Log out and sign in as `demo_tpo`.
8. Open `http://127.0.0.1:8000/tpo/analytics/` and confirm the application and status are reflected in the live analytics. TPO pages are read-only.

At the time of this check, job 8 was OPEN, owned by `demo_recruiter01`, eligible for `demo_student10`, and had no application from that student. These steps will create/update an application if you carry them out in the shared demo database.

## Verification performed

- **Existing isolated end-to-end workflow test:** `core.tests.DemoSeedCommandTests.test_seeded_student_recruiter_and_tpo_workflows_end_to_end` — passed. It exercises student login/dashboard/job detail/application/history, recruiter-owned applicant review/status update, and TPO dashboard/lists/register/analytics using the isolated test database.
- **System check:** `python manage.py check` — passed; no issues (0 silenced).
- **Complete test suite:** `python manage.py test` — passed; 85 tests in 72.654 seconds.
- **Live demo data inspected read-only:** 10 demo students, 8 demo jobs, 20 demo applications; 13 demo users. A valid un-applied student/job pair was found for the steps above.
- **Schema/migrations:** unchanged; no migration created or applied.
- **Database rows changed during this check:** none. The full test suite used Django's isolated in-memory test database; the suggested presentation workflow steps above are instructions and were not executed against the shared live database.

## Outcome

The existing presentation flow works and is covered end-to-end by the passing test. No application fix was needed. This phase is complete; no further phase was started.
