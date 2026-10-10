# Phase 9: Placement Intelligence and Analytics

## Analytics page

- Added `/tpo/analytics/`, protected by the existing TPO group authorization decorator.
- Added a link from the existing TPO dashboard and navigation links among TPO pages.
- The page uses local HTML/CSS cards, progress bars, and tables; no chart library, external CDN, analytics model, or external service was added.

## Files created

- `core/templates/core/tpo_analytics.html`: TPO analytics dashboard.
- `PHASE9_ANALYTICS_CHANGELOG.md`: Phase 9 implementation notes.

## Files modified

- `core/views.py`: read-only analytics aggregation and safe derived percentages.
- `core/urls.py`: analytics URL route.
- `core/templates/core/tpo_dashboard.html`: analytics navigation link.
- `core/templates/core/tpo_students.html`: analytics navigation link.
- `core/templates/core/tpo_student_detail.html`: analytics navigation link.
- `core/templates/core/tpo_jobs.html`: analytics navigation link.
- `core/templates/core/tpo_job_detail.html`: analytics navigation link.
- `core/templates/core/tpo_applications.html`: analytics navigation link.
- `core/tests.py`: analytics access, calculations, real skills, empty data, and optional-value coverage.

## Metrics and formulas

- **Student application rates:** students with one or more application rows divided by all Student rows; zero when the denominator is zero.
- **Students shortlisted/rejected/with offers:** distinct student IDs with at least one application of the relevant existing status.
- **Offer rates:** distinct students with an OFFERED application divided by distinct students with any application, and separately by total students. Both return zero for a zero denominator.
- **Offered applications:** count of application rows with `Application.Status.OFFERED`. This is deliberately distinguished from distinct students with offers.
- **Application funnel:** counts by existing `Application.Status` choices; each percentage uses all application rows as the denominator.
- **Job/company metrics:** counts from existing Job rows, including distinct company names, jobs with dates, status, and per-company counts. Application join counts are distinct to prevent join multiplication.
- **Required skills:** `parse_skills` supplies trimmed, deduplicated skills; case-folded exact names are counted once per job. Python/Java and Django/Flask remain distinct.
- **Match quality and skill gaps:** each Student/Job pair uses existing `evaluate_job`; match score is its `skill_match`, eligibility is its `eligible`, and missing skills come directly from its `missing_skills`. High compatibility is explicitly defined as skill match of at least 80%.
- **Readiness:** reuses the existing unweighted mean of technical, aptitude, communication, and interview scores. Distribution bands match Career Twin: High >=80, Moderate >=60 and <80, Needs improvement <60. Missing score values are treated as zero by the analytics helper.
- **Branch metrics:** average recorded CGPA and application/offer counts grouped by branch; blank branches display as “Not specified.”
- **Company metrics:** descriptive job, open-job, application, and offered-application counts; no company ranking is presented.

## Empty data behavior

- All percentage denominators are guarded; zero denominators return 0%.
- Application funnel and outcome sections display “No application data available yet.” when there are no Application rows.
- Skill demand shows a no-job-requirements message when there are no jobs or no listed skills.
- Student/job pair metrics show an empty state when either set is empty.
- Skill-gap aggregation is labeled insufficient unless there are at least two students and two jobs; it is not presented as an aggregate when the dataset is smaller.
- No chart or metric is populated with demonstration values.

## Security

- Analytics access is enforced in the view using the existing `tpo_required` decorator and `TPO` auth group.
- Anonymous users are redirected to login; authenticated users outside TPO receive 403.
- TPO analytics is read-only and has no recruiter ownership or application status mutation action.
- Existing student and recruiter authorization logic remains unchanged.

## Tests performed

- `python manage.py check`
- `python manage.py test`
- `python manage.py makemigrations --check --dry-run`
- Django test-client coverage for analytics route access, counts, distinct offer students vs offered application rows, skill normalization, matching reuse, branch/company breakdowns, zero-application data, and blank optional values.

## Known limitations

- **No fictional placement statistics are generated.**
- With the current one-student/one-job/zero-application database, application-dependent sections show their no-data states. A single available Student/Job match is shown with its pair count, but it should not be interpreted as a broad population estimate.
- Skill-gap aggregation requires at least two students and two jobs; this is a conservative threshold, not a statistical significance claim.
- Readiness and match metrics are descriptive snapshots calculated at request time from current records, not historical or predictive analytics.
- There is no separate placement-outcome model; offer analysis reflects only existing OFFERED application statuses.
