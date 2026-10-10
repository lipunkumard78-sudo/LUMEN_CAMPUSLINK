"""Deterministic matching helpers shared by CAMPUSLINK views."""


def parse_skills(value):
    """Split comma-separated skills, trim whitespace, and deduplicate case-insensitively."""
    skills = []
    seen = set()
    for raw_skill in (value or "").split(","):
        display = raw_skill.strip()
        key = display.casefold()
        if display and key not in seen:
            skills.append(display)
            seen.add(key)
    return skills


def compare_skills(student_skill_text, required_skill_text):
    """Return display-preserving matched/missing lists using exact normalized names."""
    student_skills = parse_skills(student_skill_text)
    required_skills = parse_skills(required_skill_text)
    student_by_key = {skill.casefold(): skill for skill in student_skills}
    matched = [skill.casefold() for skill in required_skills if skill.casefold() in student_by_key]
    missing = [skill.casefold() for skill in required_skills if skill.casefold() not in student_by_key]
    percentage = round(len(matched) * 100 / len(required_skills)) if required_skills else 0
    return matched, missing, percentage


def evaluate_job(student, job):
    matched, missing, percentage = compare_skills(student.skills, job.required_skills)
    cgpa_eligible = student.cgpa >= job.minimum_cgpa
    backlog_eligible = student.backlogs <= job.maximum_backlogs
    eligible = cgpa_eligible and backlog_eligible and percentage >= 50
    strengths = []
    if matched:
        strengths.append(f"Your profile lists {', '.join(matched)} required by this role.")
    if cgpa_eligible:
        strengths.append(f"Your CGPA ({student.cgpa}) meets the minimum ({job.minimum_cgpa}).")
    if backlog_eligible:
        strengths.append(f"Your backlog count ({student.backlogs}) is within the limit ({job.maximum_backlogs}).")

    why_factors = [
        f"{len(matched)} of {len(matched) + len(missing)} listed required skills match ({percentage}%).",
        f"Academic cutoff: {'met' if cgpa_eligible else 'not met'} (student {student.cgpa}, minimum {job.minimum_cgpa}).",
        f"Backlog cutoff: {'met' if backlog_eligible else 'not met'} (student {student.backlogs}, maximum {job.maximum_backlogs}).",
        "Overall eligibility requires both academic cutoffs and at least 50% exact skill coverage.",
    ]
    improvement_steps = []
    for skill in missing:
        improvement_steps.append({"step": len(improvement_steps) + 1, "title": f"Build {skill}", "description": f"{skill} is listed as a requirement and is not present in the student skill profile."})
    if not cgpa_eligible:
        improvement_steps.append({"step": len(improvement_steps) + 1, "title": "Meet the academic cutoff", "description": f"The recorded CGPA is {student.cgpa}; this role requires at least {job.minimum_cgpa}."})
    if not backlog_eligible:
        improvement_steps.append({"step": len(improvement_steps) + 1, "title": "Meet the backlog cutoff", "description": f"The recorded backlog count is {student.backlogs}; this role allows at most {job.maximum_backlogs}."})

    scores = [student.technical_score, student.aptitude_score, student.communication_score, student.interview_score]
    readiness = round(sum(scores) / len(scores))
    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "skill_match": percentage,
        "cgpa_eligible": cgpa_eligible,
        "backlog_eligible": backlog_eligible,
        "eligible": eligible,
        "readiness_score": readiness,
        "readiness_level": "High Placement Readiness" if readiness >= 80 else "Moderate Placement Readiness" if readiness >= 60 else "Needs Skill Development",
        "cgpa_gap": max(job.minimum_cgpa - student.cgpa, 0),
        "student_strengths": strengths,
        "primary_skill_gaps": missing[:3],
        "why_factors": why_factors,
        "improvement_steps": improvement_steps,
    }
