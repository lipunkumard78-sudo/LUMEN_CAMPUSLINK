from collections import Counter
from collections import defaultdict
from decimal import Decimal
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods, require_POST

from .forms import JobForm
from .models import Application, Student, Job
from .matching import compare_skills, evaluate_job, parse_skills


# ============================================================
# HOME PAGE
# ============================================================

def home(request):
    return render(request, "core/home.html")


def page_not_found(request, exception):
    return render(request, "core/404.html", status=404)


def tpo_required(view_func):
    @wraps(view_func)
    def require_tpo_group(request, *args, **kwargs):
        if not request.user.groups.filter(name="TPO").exists():
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return login_required(require_tpo_group, login_url="login")


def _readiness(student):
    return round((
        (student.technical_score or 0)
        + (student.aptitude_score or 0)
        + (student.communication_score or 0)
        + (student.interview_score or 0)
    ) / 4)


@tpo_required
def tpo_dashboard(request):
    students = list(Student.objects.all())
    jobs = list(Job.objects.annotate(applicant_count=Count("applications")))
    applications = Application.objects.all()
    scores = [_readiness(student) for student in students]
    readiness_students = [
        {"student": student, "readiness": score}
        for student, score in zip(students, scores)
    ]
    gap_counts = Counter(
        skill.casefold()
        for student in students
        for job in jobs
        for skill in compare_skills(student.skills, job.required_skills)[1]
    )
    status_counts = {
        status: applications.filter(status=status).count()
        for status, _label in Application.Status.choices
    }
    return render(request, "core/tpo_dashboard.html", {
        "readiness_students": readiness_students,
        "jobs": jobs,
        "student_count": len(students),
        "job_count": len(jobs),
        "open_job_count": Job.objects.filter(status=Job.Status.OPEN).count(),
        "closed_job_count": Job.objects.filter(status=Job.Status.CLOSED).count(),
        "application_count": applications.count(),
        "applied_count": status_counts[Application.Status.APPLIED],
        "shortlisted_count": status_counts[Application.Status.SHORTLISTED],
        "rejected_count": status_counts[Application.Status.REJECTED],
        "offered_count": status_counts[Application.Status.OFFERED],
        "students_with_offers": Student.objects.filter(
            applications__status=Application.Status.OFFERED
        ).distinct().count(),
        "total_offers": status_counts[Application.Status.OFFERED],
        "average_readiness": round(sum(scores) / len(scores)) if scores else 0,
        "high_readiness_count": sum(score >= 80 for score in scores),
        "top_skill_gaps": gap_counts.most_common(8),
    })


def _percentage(numerator, denominator):
    return round(numerator * 100 / denominator) if denominator else 0


@tpo_required
def tpo_analytics(request):
    students = list(Student.objects.all())
    jobs = list(Job.objects.all())
    applications = Application.objects.all()
    total_students = len(students)
    total_jobs = len(jobs)
    total_applications = applications.count()

    applicants = applications.values("student_id").distinct().count()
    students_applied = applicants
    students_shortlisted = applications.filter(
        status=Application.Status.SHORTLISTED
    ).values("student_id").distinct().count()
    students_rejected = applications.filter(
        status=Application.Status.REJECTED
    ).values("student_id").distinct().count()
    students_with_offers = applications.filter(
        status=Application.Status.OFFERED
    ).values("student_id").distinct().count()
    offered_applications = applications.filter(
        status=Application.Status.OFFERED
    ).count()

    status_counts = {
        status: applications.filter(status=status).count()
        for status, _label in Application.Status.choices
    }
    application_funnel = [
        {
            "value": value,
            "label": label,
            "count": status_counts[value],
            "percentage": _percentage(status_counts[value], total_applications),
        }
        for value, label in Application.Status.choices
    ]

    skill_job_counts = Counter()
    skill_labels = {}
    for job in jobs:
        seen_for_job = set()
        for skill in parse_skills(job.required_skills):
            normalized = skill.casefold()
            if normalized not in seen_for_job:
                skill_job_counts[normalized] += 1
                skill_labels.setdefault(normalized, skill)
                seen_for_job.add(normalized)
    top_required_skills = [
        {"skill": skill_labels[skill], "job_count": count}
        for skill, count in sorted(
            skill_job_counts.items(), key=lambda entry: (-entry[1], entry[0])
        )[:10]
    ]

    match_results = [
        evaluate_job(student, job)
        for student in students
        for job in jobs
    ]
    evaluated_pairs = len(match_results)
    average_match_score = (
        round(sum(result["skill_match"] for result in match_results) / evaluated_pairs)
        if evaluated_pairs else 0
    )
    highly_compatible_matches = sum(
        result["skill_match"] >= 80 for result in match_results
    )
    eligible_matches = sum(result["eligible"] for result in match_results)
    ineligible_matches = evaluated_pairs - eligible_matches

    skill_gap_counts = Counter(
        skill
        for result in match_results
        for skill in result["missing_skills"]
    )
    skill_gap_is_aggregate = total_students >= 2 and total_jobs >= 2
    match_is_aggregate = total_students >= 2 and total_jobs >= 2
    frequent_skill_gaps = [
        {"skill": skill, "pair_count": count}
        for skill, count in skill_gap_counts.most_common(10)
    ] if skill_gap_is_aggregate else []

    readiness_by_student = [
        {"student": student, "score": _readiness(student)}
        for student in students
    ]
    readiness_scores = [item["score"] for item in readiness_by_student]
    readiness_distribution = [
        {"label": "High (80-100)", "count": sum(score >= 80 for score in readiness_scores)},
        {"label": "Moderate (60-79)", "count": sum(60 <= score < 80 for score in readiness_scores)},
        {"label": "Needs improvement (<60)", "count": sum(score < 60 for score in readiness_scores)},
    ]

    branch_students = defaultdict(list)
    for student in students:
        branch_students[student.branch or "Not specified"].append(student)
    branch_application_counts = Counter(
        (branch or "Not specified", status)
        for branch, status in applications.values_list("student__branch", "status")
    )
    branch_analysis = []
    for branch, branch_group in sorted(branch_students.items()):
        average_cgpa = sum(
            (student.cgpa for student in branch_group if student.cgpa is not None),
            Decimal("0"),
        )
        cgpa_count = sum(student.cgpa is not None for student in branch_group)
        branch_analysis.append({
            "branch": branch,
            "student_count": len(branch_group),
            "average_cgpa": (average_cgpa / cgpa_count).quantize(Decimal("0.01")) if cgpa_count else None,
            "application_count": sum(
                branch_application_counts[(branch, status)]
                for status, _label in Application.Status.choices
            ),
            "offer_count": branch_application_counts[(branch, Application.Status.OFFERED)],
        })

    company_analysis = list(
        Job.objects.order_by().values("company_name").annotate(
            job_count=Count("id", distinct=True),
            open_job_count=Count("id", filter=Q(status=Job.Status.OPEN), distinct=True),
            application_count=Count("applications", distinct=True),
            offer_count=Count(
                "applications",
                filter=Q(applications__status=Application.Status.OFFERED),
                distinct=True,
            ),
        ).order_by("company_name")
    )

    return render(request, "core/tpo_analytics.html", {
        "total_students": total_students,
        "students_with_applications": students_applied,
        "students_shortlisted": students_shortlisted,
        "students_rejected": students_rejected,
        "students_with_offers": students_with_offers,
        "students_without_applications": total_students - students_applied,
        "application_rate": _percentage(students_applied, total_students),
        "offer_rate_all_students": _percentage(students_with_offers, total_students),
        "offer_rate_applicants": _percentage(students_with_offers, students_applied),
        "total_jobs": total_jobs,
        "open_jobs": sum(job.status == Job.Status.OPEN for job in jobs),
        "closed_jobs": sum(job.status == Job.Status.CLOSED for job in jobs),
        "jobs_with_deadlines": sum(job.deadline is not None for job in jobs),
        "jobs_with_drive_dates": sum(job.drive_date is not None for job in jobs),
        "companies_represented": len({job.company_name for job in jobs}),
        "total_applications": total_applications,
        "application_funnel": application_funnel,
        "offered_applications": offered_applications,
        "top_required_skills": top_required_skills,
        "frequent_skill_gaps": frequent_skill_gaps,
        "skill_gap_is_aggregate": skill_gap_is_aggregate,
        "match_is_aggregate": match_is_aggregate,
        "evaluated_pairs": evaluated_pairs,
        "average_match_score": average_match_score,
        "highly_compatible_matches": highly_compatible_matches,
        "eligible_matches": eligible_matches,
        "ineligible_matches": ineligible_matches,
        "average_readiness": round(sum(readiness_scores) / total_students) if total_students else 0,
        "readiness_distribution": readiness_distribution,
        "readiness_by_student": readiness_by_student,
        "students_needing_improvement": sum(score < 60 for score in readiness_scores),
        "branch_analysis": branch_analysis,
        "company_analysis": company_analysis,
        "has_application_data": total_applications > 0,
        "has_matching_data": evaluated_pairs > 0,
    })


@tpo_required
def tpo_students(request):
    students = Student.objects.order_by("name")
    student_rows = [
        {"student": student, "readiness": _readiness(student)}
        for student in students
    ]
    return render(request, "core/tpo_students.html", {"student_rows": student_rows})


@tpo_required
def tpo_student_detail(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    applications = student.applications.select_related("job").order_by("-applied_at")
    return render(request, "core/tpo_student_detail.html", {
        "student": student,
        "readiness": _readiness(student),
        "applications": applications,
    })


@tpo_required
def tpo_jobs(request):
    jobs = Job.objects.select_related("recruiter").annotate(
        applicant_count=Count("applications")
    ).order_by("company_name", "job_title")
    return render(request, "core/tpo_jobs.html", {"jobs": jobs})


@tpo_required
def tpo_job_detail(request, job_id):
    job = get_object_or_404(
        Job.objects.select_related("recruiter").annotate(
            applicant_count=Count("applications")
        ),
        pk=job_id,
    )
    return render(request, "core/tpo_job_detail.html", {"job": job})


@tpo_required
def tpo_applications(request):
    applications = Application.objects.select_related("student", "job")
    selected_status = request.GET.get("status", "")
    selected_job = request.GET.get("job", "")
    selected_company = request.GET.get("company", "")
    selected_student = request.GET.get("student", "")
    selected_branch = request.GET.get("branch", "")

    if selected_status in Application.Status.values:
        applications = applications.filter(status=selected_status)
    if selected_job.isdigit() and Job.objects.filter(pk=selected_job).exists():
        applications = applications.filter(job_id=selected_job)
    companies = list(Job.objects.order_by().values_list("company_name", flat=True).distinct())
    if selected_company in companies:
        applications = applications.filter(job__company_name=selected_company)
    if selected_student.isdigit() and Student.objects.filter(pk=selected_student).exists():
        applications = applications.filter(student_id=selected_student)
    branches = list(Student.objects.order_by().values_list("branch", flat=True).distinct())
    if selected_branch in branches:
        applications = applications.filter(student__branch=selected_branch)

    application_rows = [
        {
            "application": application,
            "match_score": evaluate_job(application.student, application.job)["skill_match"],
        }
        for application in applications.order_by("-applied_at")
    ]
    return render(request, "core/tpo_applications.html", {
        "application_rows": application_rows,
        "statuses": Application.Status.choices,
        "jobs": Job.objects.order_by("company_name", "job_title"),
        "companies": companies,
        "students": Student.objects.order_by("name"),
        "branches": branches,
        "selected_status": selected_status,
        "selected_job": selected_job,
        "selected_company": selected_company,
        "selected_student": selected_student,
        "selected_branch": selected_branch,
    })


def recruiter_required(view_func):
    @wraps(view_func)
    def require_recruiter_group(request, *args, **kwargs):
        if not request.user.groups.filter(name="RECRUITER").exists():
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return login_required(require_recruiter_group, login_url="login")


def _recruiter_jobs(user):
    return Job.objects.filter(recruiter=user)


def student_required(view_func):
    @wraps(view_func)
    def require_linked_student(request, *args, **kwargs):
        if not request.user.groups.filter(name="STUDENT").exists():
            raise PermissionDenied
        student = Student.objects.filter(user=request.user).first()
        if student is None:
            return render(request, "core/student_profile_linking.html")
        request.student_profile = student
        return view_func(request, *args, **kwargs)

    return login_required(require_linked_student, login_url="login")


@recruiter_required
def recruiter_dashboard(request):
    jobs = _recruiter_jobs(request.user)
    applications = Application.objects.filter(job__recruiter=request.user)
    context = {
        "jobs": jobs.annotate(applicant_count=Count("applications")).order_by("-created_at"),
        "total_jobs": jobs.count(),
        "open_jobs": jobs.filter(status=Job.Status.OPEN).count(),
        "closed_jobs": jobs.filter(status=Job.Status.CLOSED).count(),
        "total_applications": applications.count(),
        "shortlisted_count": applications.filter(status=Application.Status.SHORTLISTED).count(),
        "rejected_count": applications.filter(status=Application.Status.REJECTED).count(),
        "offered_count": applications.filter(status=Application.Status.OFFERED).count(),
    }
    return render(request, "core/recruiter_dashboard.html", context)


@recruiter_required
def recruiter_jobs(request):
    jobs = _recruiter_jobs(request.user).annotate(
        applicant_count=Count("applications")
    ).order_by("-created_at")
    return render(request, "core/recruiter_jobs.html", {"jobs": jobs})


@recruiter_required
@require_http_methods(["GET", "POST"])
def recruiter_job_create(request):
    form = JobForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        job = form.save(commit=False)
        job.recruiter = request.user
        job.status = Job.Status.OPEN
        job.save()
        return redirect("recruiter_jobs")
    return render(request, "core/recruiter_job_form.html", {
        "form": form,
        "page_title": "Create Job",
        "submit_label": "Create job",
    })


@recruiter_required
@require_http_methods(["GET", "POST"])
def recruiter_job_edit(request, job_id):
    job = get_object_or_404(_recruiter_jobs(request.user), pk=job_id)
    form = JobForm(request.POST or None, instance=job)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("recruiter_job_detail", job_id=job.id)
    return render(request, "core/recruiter_job_form.html", {
        "form": form,
        "job": job,
        "page_title": "Edit Job",
        "submit_label": "Save changes",
    })


@recruiter_required
def recruiter_job_detail(request, job_id):
    job = get_object_or_404(
        _recruiter_jobs(request.user).annotate(applicant_count=Count("applications")),
        pk=job_id,
    )
    return render(request, "core/recruiter_job_detail.html", {"job": job})


@recruiter_required
@require_POST
def recruiter_job_toggle_status(request, job_id):
    job = get_object_or_404(_recruiter_jobs(request.user), pk=job_id)
    job.status = (
        Job.Status.CLOSED if job.status == Job.Status.OPEN else Job.Status.OPEN
    )
    job.save(update_fields=["status"])
    return redirect("recruiter_jobs")


@recruiter_required
def recruiter_applications(request, job_id):
    job = get_object_or_404(_recruiter_jobs(request.user), pk=job_id)
    applications = (
        Application.objects.filter(job=job)
        .select_related("student")
        .order_by("-applied_at")
    )
    applicants = []
    for application in applications:
        evaluation = evaluate_job(application.student, job)
        applicants.append({
            "application": application,
            "student": application.student,
            "college": getattr(application.student, "college", None) or "Not recorded",
            "match_score": evaluation["skill_match"],
            "eligible": evaluation["eligible"],
        })
    return render(request, "core/recruiter_applications.html", {
        "job": job,
        "applicants": applicants,
        "has_matching_applicants": any(item["match_score"] > 0 for item in applicants),
        "statuses": Application.Status.choices,
        "shortlisted_count": sum(
            item["application"].status == Application.Status.SHORTLISTED
            for item in applicants
        ),
    })


@recruiter_required
@require_POST
def recruiter_application_status(request, application_id):
    application = get_object_or_404(
        Application.objects.select_related("job"),
        pk=application_id,
        job__recruiter=request.user,
    )
    status = request.POST.get("status")
    if status not in Application.Status.values:
        return HttpResponseBadRequest("Invalid application status.")
    application.status = status
    application.save(update_fields=["status"])
    return redirect("recruiter_applications", job_id=application.job_id)


# ============================================================
# STUDENT DASHBOARD
# ============================================================

@student_required
def student_dashboard(request):
    student = request.student_profile
    applications_by_job = {
        application.job_id: application
        for application in Application.objects.filter(student=student).select_related("job")
    }

    readiness = 0
    readiness_level = "No Assessment Data"
    skill_match = 0
    matched_skills = []
    missing_skills = []
    target_role = "Software Developer"
    target_job = None
    job_opportunities = []

    if student:
        # Calculate 360 readiness score from existing assessment fields
        scores = [
            student.technical_score,
            student.aptitude_score,
            student.communication_score,
            student.interview_score,
        ]
        if any(scores):
            readiness = round(sum(scores) / len(scores))
            if readiness >= 80:
                readiness_level = "High Placement Readiness"
            elif readiness >= 60:
                readiness_level = "Moderate Placement Readiness"
            else:
                readiness_level = "Needs Skill Development"
        else:
            readiness = 0
            readiness_level = "Assessments Pending"

        student_skills = {skill.casefold() for skill in parse_skills(student.skills)}

        # Target job for benchmark skill gap analysis
        target_job = (
            Job.objects.filter(job_title__icontains=target_role).first()
            or Job.objects.first()
        )

        if target_job:
            target_role = target_job.job_title
            matched_skills, missing_skills, skill_match = compare_skills(
                student.skills, target_job.required_skills
            )

        # Evaluate the linked student's eligibility and application state per job.
        for job in Job.objects.all():
            evaluation = evaluate_job(student, job)
            job_opportunities.append(
                {
                    "job": job,
                    "application": applications_by_job.get(job.id),
                    **evaluation,
                }
            )

    context = {
        "student": student,
        "application_count": len(applications_by_job),
        "readiness": readiness,
        "readiness_level": readiness_level,
        "skill_match": skill_match,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "target_role": target_role,
        "target_job": target_job,
        "job_opportunities": job_opportunities,
    }

    return render(
        request,
        "core/student_dashboard.html",
        context
    )


# ============================================================
# CAREER TWIN
# ============================================================

@student_required
def career_twin(request):
    student = request.student_profile

    # 1. 360° Readiness Scoring
    scores = {
        "Technical": student.technical_score,
        "Aptitude": student.aptitude_score,
        "Communication": student.communication_score,
        "Interview": student.interview_score,
    }
    score_vals = list(scores.values())
    readiness = (
        round(sum(score_vals) / len(score_vals)) if any(score_vals) else 0
    )

    if readiness >= 80:
        readiness_level = "High Placement Readiness"
        readiness_badge_class = "level-high"
    elif readiness >= 60:
        readiness_level = "Moderate Placement Readiness"
        readiness_badge_class = "level-moderate"
    else:
        readiness_level = "Needs Skill Development"
        readiness_badge_class = "level-developing"

    # Identify strongest and weakest pillars
    strongest_pillar = max(scores.items(), key=lambda x: x[1])
    weakest_pillar = min(scores.items(), key=lambda x: x[1])

    # 2. Student Skill Profile
    student_skills = [s.casefold() for s in parse_skills(student.skills)]
    student_skills_display = parse_skills(student.skills)

    # 3. Job Analysis & Skill Gaps against all active jobs
    jobs = Job.objects.all()
    role_analyses = []
    all_missing_skills = []
    all_matched_skills = set()
    eligible_count = 0

    for job in jobs:
        req_skills = [s.casefold() for s in parse_skills(job.required_skills)]
        matched = [s for s in req_skills if s in student_skills]
        missing = [s for s in req_skills if s not in student_skills]
        match_pct = (
            round((len(matched) / len(req_skills)) * 100) if req_skills else 0
        )

        cgpa_ok = student.cgpa >= job.minimum_cgpa
        backlogs_ok = student.backlogs <= job.maximum_backlogs
        eligible = cgpa_ok and backlogs_ok and match_pct >= 50

        if eligible:
            eligible_count += 1

        all_matched_skills.update(matched)
        all_missing_skills.extend(missing)

        role_analyses.append(
            {
                "job": job,
                "required_skills": req_skills,
                "matched_skills": matched,
                "missing_skills": missing,
                "match_pct": match_pct,
                "cgpa_ok": cgpa_ok,
                "backlogs_ok": backlogs_ok,
                "eligible": eligible,
            }
        )

    # Sort role analyses by match percentage descending
    role_analyses.sort(key=lambda x: x["match_pct"], reverse=True)

    # Missing skill frequency across all jobs
    missing_freq = Counter(all_missing_skills)
    top_missing_skills = [
        skill for skill, count in missing_freq.most_common(6)
    ]

    # Target Career Roles (distinct job titles)
    target_roles = list(dict.fromkeys(job.job_title for job in jobs))

    # 4. Explainable Recommendations Engine (Deterministic)
    recommendations = []

    # Recommendation 1: Skill Gap Remediation
    if top_missing_skills:
        primary_skills_str = ", ".join(
            s.title() for s in top_missing_skills[:3]
        )
        recommendations.append(
            {
                "category": "Skill Gap Remediation",
                "icon": "⚡",
                "title": f"Prioritize Learning: {primary_skills_str}",
                "description": (
                    f"Your profile lacks {len(top_missing_skills)} skill(s) actively sought by campus recruiters. "
                    f"Prioritizing {primary_skills_str} will yield the highest incremental compatibility "
                    f"across active placement drives."
                ),
                "impact": f"+{min(len(top_missing_skills)*15, 45)}% Potential Match Increase",
                "type": "skill",
            }
        )
    else:
        recommendations.append(
            {
                "category": "Skill Gap Remediation",
                "icon": "✅",
                "title": "Full Skill Alignment",
                "description": (
                    "Your current skill profile encompasses all requirements across currently posted drives."
                ),
                "impact": "Optimal Compatibility",
                "type": "success",
            }
        )

    # Recommendation 2: Assessment Readiness Gain
    potential_readiness_gain = round(10 / 4)
    new_readiness = min(100, readiness + potential_readiness_gain)
    recommendations.append(
        {
            "category": "Readiness Optimization",
            "icon": "🎯",
            "title": f"Elevate {weakest_pillar[0]} Performance (Currently {weakest_pillar[1]}/100)",
            "description": (
                f"Your {weakest_pillar[0]} score is your primary growth vector. "
                f"Targeting a 10-point improvement in {weakest_pillar[0]} (from {weakest_pillar[1]} to {min(100, weakest_pillar[1]+10)}) "
                f"will directly elevate your composite Placement Readiness Index from {readiness}% to {new_readiness}%."
            ),
            "impact": f"+{potential_readiness_gain}% Composite Readiness Boost",
            "type": "readiness",
        }
    )

    # Recommendation 3: Academic & Drive Eligibility
    total_jobs = jobs.count()
    if total_jobs > 0:
        if eligible_count == total_jobs:
            eligibility_desc = (
                "You meet CGPA, backlog, and skill criteria for all currently active campus placement drives."
            )
        elif eligible_count > 0:
            eligibility_desc = (
                f"You are currently qualified for {eligible_count} out of {total_jobs} active drives. "
                f"Bridge the skill threshold (>=50%) to qualify for remaining drives."
            )
        else:
            eligibility_desc = (
                f"While your CGPA ({student.cgpa}) and backlog status ({student.backlogs}) satisfy basic criteria, "
                f"you need at least 50% skill match on candidate drives to unlock shortlisting eligibility."
            )
        recommendations.append(
            {
                "category": "Drive Qualification Strategy",
                "icon": "📋",
                "title": f"Drive Qualification: {eligible_count} of {total_jobs} Eligible",
                "description": eligibility_desc,
                "impact": f"{eligible_count}/{total_jobs} Drives Qualified",
                "type": "eligibility",
            }
        )

    # Recommendation 4: Project & Practical Demonstration
    if student.projects:
        recommendations.append(
            {
                "category": "Portfolio & Practical Proof",
                "icon": "🚀",
                "title": f"Demonstrate '{student.projects}' in Repositories",
                "description": (
                    f"Convert your capstone project '{student.projects}' into a publicly verifiable GitHub portfolio. "
                    "Integrate unit testing and clear documentation to validate your technical mastery during interviews."
                ),
                "impact": "High Interview Convertibility",
                "type": "project",
            }
        )

    context = {
        "student": student,
        "scores": scores,
        "readiness": readiness,
        "readiness_level": readiness_level,
        "readiness_badge_class": readiness_badge_class,
        "strongest_pillar": strongest_pillar,
        "weakest_pillar": weakest_pillar,
        "student_skills_display": student_skills_display,
        "target_roles": target_roles,
        "role_analyses": role_analyses,
        "top_missing_skills": top_missing_skills,
        "all_matched_skills": list(all_matched_skills),
        "recommendations": recommendations,
        "institution": "BPUT / Affiliated Institution",
    }

    return render(
        request,
        "core/career_twin.html",
        context
    )


# ============================================================
# ADD STUDENT
# ============================================================

def add_student(request):

    if request.method == "POST":

        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        branch = request.POST.get("branch")
        semester = request.POST.get("semester")

        cgpa = request.POST.get("cgpa")
        backlogs = request.POST.get("backlogs")

        technical_score = request.POST.get(
            "technical_score", 0
        )

        aptitude_score = request.POST.get(
            "aptitude_score", 0
        )

        communication_score = request.POST.get(
            "communication_score", 0
        )

        interview_score = request.POST.get(
            "interview_score", 0
        )

        skills = request.POST.get("skills", "")

        projects = request.POST.get(
            "projects", ""
        )

        certifications = request.POST.get(
            "certifications", ""
        )


        # ----------------------------------------------------
        # CREATE STUDENT
        # ----------------------------------------------------

        Student.objects.create(

            name=name,

            email=email,

            phone=phone,

            branch=branch,

            semester=semester,

            cgpa=cgpa,

            backlogs=backlogs,

            technical_score=technical_score,

            aptitude_score=aptitude_score,

            communication_score=communication_score,

            interview_score=interview_score,

            skills=skills,

            projects=projects,

            certifications=certifications,
        )


        # After adding student,
        # go to student dashboard

        return redirect("student_dashboard")


    # If request is GET,
    # show add student page

    return render(
        request,
        "core/add_student.html"
    )


# ============================================================
# JOB MATCHING
# ============================================================

def job_match(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    student = None
    application = None
    context = {"student": student, "job": job}

    if request.user.is_authenticated and request.user.groups.filter(name="STUDENT").exists():
        student = Student.objects.filter(user=request.user).first()
        if student:
            context.update(evaluate_job(student, job))
            application = Application.objects.filter(student=student, job=job).first()
            context["student"] = student
            context["application"] = application
            context["profile_link_required"] = False
        else:
            context["profile_link_required"] = True

    return render(request, "core/job_match.html", context)


@student_required
@require_POST
def apply_to_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    student = request.student_profile
    existing_application = Application.objects.filter(student=student, job=job).first()

    if existing_application:
        messages.info(request, "You have already applied for this job.")
    elif job.status != Job.Status.OPEN:
        messages.error(request, "This job is closed and is no longer accepting applications.")
    else:
        evaluation = evaluate_job(student, job)
        if not evaluation["eligible"]:
            reasons = []
            if not evaluation["cgpa_eligible"]:
                reasons.append(f"CGPA must be at least {job.minimum_cgpa}.")
            if not evaluation["backlog_eligible"]:
                reasons.append(f"Backlogs must not exceed {job.maximum_backlogs}.")
            if evaluation["skill_match"] < 50:
                reasons.append("At least 50% of required skills must match.")
            messages.error(request, "You are not eligible to apply. " + " ".join(reasons))
        else:
            application, created = Application.objects.get_or_create(
                student=student,
                job=job,
                defaults={"status": Application.Status.APPLIED},
            )
            if created:
                messages.success(request, "Your application has been submitted.")
            else:
                messages.info(request, "You have already applied for this job.")

    return redirect("job_match", job_id=job.id)


@student_required
def student_applications(request):
    student = request.student_profile
    applications = (
        Application.objects.filter(student=student)
        .select_related("job")
        .order_by("-applied_at")
    )
    application_items = [
        {
            "application": application,
            "match_score": evaluate_job(student, application.job)["skill_match"],
        }
        for application in applications
    ]
    return render(request, "core/student_applications.html", {
        "applications": application_items,
    })
