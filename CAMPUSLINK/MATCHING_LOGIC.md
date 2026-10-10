# CAMPUSLINK Matching Logic

## Skill comparison

Skills are comma-separated values from the existing `Student.skills` and `Job.required_skills` fields.

1. Split on commas and trim surrounding whitespace.
2. Ignore empty entries.
3. Compare exact skill strings with Unicode case folding, so `Python`, `python`, and `PYTHON` match.
4. Repeated entries that differ only by case or surrounding whitespace count once.
5. Do not infer synonyms or related technologies: Python does not equal Java, Django does not equal Flask, and SQL does not equal MongoDB.
6. A match percentage is `round(matched required skills / unique required skills * 100)`. With no listed requirements, it is 0%.

## Academic eligibility

- CGPA passes when the recorded student CGPA is greater than or equal to the job minimum.
- Backlog eligibility passes when the recorded backlog count is less than or equal to the job maximum.
- Overall eligibility requires both academic checks and at least 50% skill coverage.

## Readiness

Readiness is the rounded arithmetic mean of technical, aptitude, communication, and interview scores already stored for the student. It contributes context and is not part of the current eligibility threshold.

## Explainability

Job match explanations enumerate matched and missing required skills, each academic cutoff, the overall threshold, and improvement suggestions from recorded missing requirements or failed academic cutoffs. The calculations are deterministic for a fixed Student and Job record.
