from datetime import date
from decimal import Decimal

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import Group, User
from django.core.management import call_command, CommandError
from io import StringIO
from core.models import Application, Student, Job
from core.matching import compare_skills, evaluate_job
from core.management.commands.seed_demo_data import DEMO_PASSWORD


class CampusLinkPhaseTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Seed test student matching existing Rahul Kumar profile
        self.student = Student.objects.create(
            name="Rahul Kumar",
            email="rahul@test.com",
            phone="9876543210",
            branch="MCA",
            semester=1,
            cgpa=8.20,
            backlogs=0,
            skills="Python, SQL, Django, HTML, CSS, C",
            projects="Smart Clinic Management System",
            certifications="Python Programming Certificate",
            technical_score=75,
            aptitude_score=72,
            communication_score=68,
            interview_score=70,
        )
        # Seed test job matching existing TCS Software Developer listing
        self.job = Job.objects.create(
            company_name="TCS",
            job_title="Software Developer",
            description="Entry-level software developer position for MCA and computer science students.",
            required_skills="Python, SQL, Data Structures, Algorithms, Git, OOPS",
            minimum_cgpa=6.00,
            maximum_backlogs=0,
            location="Bhubaneswar",
            package="5 LPA",
        )

    def login_as_student(self):
        student_group, _ = Group.objects.get_or_create(name="STUDENT")
        user = User.objects.create(username="linked_student", password="unused")
        user.groups.add(student_group)
        self.student.user = user
        self.student.save(update_fields=["user"])
        self.client.force_login(user)
        return user

    # ============================================================
    # PHASE 1 TESTS (PRESERVED)
    # ============================================================

    def test_student_model_str(self):
        self.assertEqual(str(self.student), "Rahul Kumar")

    def test_job_model_str(self):
        self.assertEqual(str(self.job), "TCS - Software Developer")

    def test_home_page(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")
        self.assertContains(response, "CAMPUS")
        self.assertContains(response, "Explore CAMPUSLINK")

    def test_student_dashboard_renders_and_computes_readiness(self):
        self.login_as_student()
        response = self.client.get(reverse("student_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/student_dashboard.html")
        self.assertTemplateUsed(response, "core/base.html")

        # Test context values computed dynamically
        self.assertEqual(response.context["student"], self.student)
        # (75 + 72 + 68 + 70) / 4 = 71.25 -> 71
        self.assertEqual(response.context["readiness"], 71)
        self.assertEqual(response.context["readiness_level"], "Moderate Placement Readiness")

        # Skill match test: 2 matched (python, sql) out of 6 required = 33%
        self.assertEqual(response.context["skill_match"], 33)
        self.assertIn("python", response.context["matched_skills"])
        self.assertIn("sql", response.context["matched_skills"])
        self.assertIn("git", response.context["missing_skills"])

        # Check opportunities list
        self.assertEqual(len(response.context["job_opportunities"]), 1)
        opp = response.context["job_opportunities"][0]
        self.assertEqual(opp["job"], self.job)
        self.assertTrue(opp["cgpa_eligible"])
        self.assertTrue(opp["backlog_eligible"])
        self.assertFalse(opp["eligible"])

        # Verify rendered content
        self.assertContains(response, "Rahul Kumar")
        self.assertContains(response, "71%")
        self.assertContains(response, "Moderate Placement Readiness")
        self.assertContains(response, "33% Skill Compatibility")
        self.assertContains(response, "TCS")
        self.assertContains(response, "Open Career Twin Persona")
        self.assertContains(response, "No applications yet")

    def test_job_match_existing_job(self):
        self.login_as_student()
        response = self.client.get(reverse("job_match", args=[self.job.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/job_match.html")
        self.assertEqual(response.context["skill_match"], 33)
        self.assertEqual(response.context["readiness_score"], 71)
        self.assertTrue(response.context["cgpa_eligible"])
        self.assertTrue(response.context["backlog_eligible"])
        self.assertFalse(response.context["eligible"])
        self.assertContains(response, "TCS")
        self.assertContains(response, "Software Developer")
        self.assertContains(response, "33%")
        self.assertContains(response, "2 matched · 4 gaps")

    def test_skill_matching_normalizes_case_and_whitespace_only(self):
        matched, missing, percentage = compare_skills(
            " Python, python , SQL ", "python, Django, SQL"
        )
        self.assertEqual(matched, ["python", "sql"])
        self.assertEqual(missing, ["django"])
        self.assertEqual(percentage, 67)
        self.assertEqual(compare_skills("Python", "Java")[0], [])
        self.assertEqual(compare_skills("Django", "Flask")[0], [])
        self.assertEqual(compare_skills("SQL", "MongoDB")[0], [])

    def test_job_match_explanation_uses_recorded_requirements(self):
        first = evaluate_job(self.student, self.job)
        second = evaluate_job(self.student, self.job)
        self.assertEqual(first, second)
        self.assertEqual(first["matched_skills"], ["python", "sql"])
        self.assertEqual(first["missing_skills"], ["data structures", "algorithms", "git", "oops"])
        self.assertEqual(first["readiness_score"], 71)
        self.assertEqual(len(first["why_factors"]), 4)
        self.assertEqual(len(first["improvement_steps"]), 4)

    def test_job_match_view_populates_explanation_sections(self):
        self.login_as_student()
        response = self.client.get(reverse("job_match", args=[self.job.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["why_factors"])
        self.assertTrue(response.context["improvement_steps"])
        self.assertContains(response, "Why This Match Result Exists")
        self.assertContains(response, "Build data structures")

    def test_tpo_dashboard_requires_tpo_group(self):
        url = reverse("tpo_dashboard")
        anonymous_response = self.client.get(url)
        self.assertEqual(anonymous_response.status_code, 302)

        ordinary_user = User.objects.create_user(username="student_user", password="safe-test-pass")
        self.client.force_login(ordinary_user)
        self.assertEqual(self.client.get(url).status_code, 403)

        tpo_group, _ = Group.objects.get_or_create(name="TPO")
        ordinary_user.groups.add(tpo_group)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["student_count"], 1)
        self.assertEqual(response.context["average_readiness"], 71)
        self.assertContains(response, "Rahul Kumar")
        self.assertContains(response, "data structures")

    def test_non_student_user_cannot_view_career_twin(self):
        ordinary_user = User.objects.create(username="career_twin_non_student")
        self.client.force_login(ordinary_user)
        self.assertEqual(self.client.get(reverse("career_twin")).status_code, 403)

    def test_job_match_nonexistent_job_returns_404(self):
        response = self.client.get(reverse("job_match", args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_job_is_404_when_no_student_exists(self):
        Student.objects.all().delete()
        response = self.client.get(reverse("job_match", args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_admin_login_accessible(self):
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Django administration")

    def test_student_dashboard_empty_db_graceful(self):
        self.login_as_student()
        Student.objects.all().delete()
        response = self.client.get(reverse("student_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student profile not linked")

    # ============================================================
    # PHASE 2 TESTS: CAMPUSLINK CAREER TWIN
    # ============================================================

    def test_career_twin_page_renders_successfully(self):
        self.login_as_student()
        response = self.client.get(reverse("career_twin"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/career_twin.html")
        self.assertTemplateUsed(response, "core/base.html")

        # Context checks
        self.assertEqual(response.context["student"], self.student)
        self.assertEqual(response.context["readiness"], 71)
        self.assertEqual(response.context["readiness_level"], "Moderate Placement Readiness")
        self.assertEqual(response.context["strongest_pillar"], ("Technical", 75))
        self.assertEqual(response.context["weakest_pillar"], ("Communication", 68))
        self.assertIn("Software Developer", response.context["target_roles"])

        # Rendered HTML checks
        self.assertContains(response, "Rahul Kumar")
        self.assertContains(response, "Career Twin 360")
        self.assertContains(response, "71%")
        self.assertContains(response, "Moderate Placement Readiness")
        self.assertContains(response, "Technical Proficiency")
        self.assertContains(response, "Aptitude &amp; Problem Solving")
        self.assertContains(response, "Communication &amp; Articulation")
        self.assertContains(response, "Interview Performance")
        self.assertContains(response, "TCS")
        self.assertContains(response, "Software Developer")
        self.assertContains(response, "Explainable Career Recommendations")

    def test_career_twin_student_view_does_not_offer_profile_switching(self):
        self.login_as_student()
        other_student = Student.objects.create(
            name="Private Dashboard Record",
            email="private-dashboard@example.com",
            phone="1234567890",
            branch="Physics",
            semester=2,
            cgpa=7.0,
            backlogs=0,
            skills="Physics",
        )
        response = self.client.get(reverse("career_twin"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["student"], self.student)
        self.assertNotContains(response, other_student.name)
        self.assertNotContains(response, "student_id=")

    def test_career_twin_readiness_calculation(self):
        student_user = self.login_as_student()
        # High readiness student (>= 80)
        high_student = Student.objects.create(
            name="Priya Sharma",
            email="priya@test.com",
            phone="9123456789",
            branch="Computer Science",
            semester=2,
            cgpa=9.1,
            backlogs=0,
            skills="Python, SQL, Java, Git, OOPS",
            technical_score=90,
            aptitude_score=85,
            communication_score=80,
            interview_score=85,
        )
        self.student.user = None
        self.student.save(update_fields=["user"])
        high_student.user = student_user
        high_student.save(update_fields=["user"])
        response = self.client.get(reverse("career_twin") + f"?student_id={self.student.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["student"], high_student)
        # (90 + 85 + 80 + 85) / 4 = 85
        self.assertEqual(response.context["readiness"], 85)
        self.assertEqual(response.context["readiness_level"], "High Placement Readiness")

        # Developing student (< 60)
        dev_student = Student.objects.create(
            name="Amit Patel",
            email="amit@test.com",
            phone="9988776655",
            branch="Mechanical",
            semester=1,
            cgpa=6.5,
            backlogs=1,
            skills="C, AutoCAD",
            technical_score=50,
            aptitude_score=45,
            communication_score=55,
            interview_score=50,
        )
        high_student.user = None
        high_student.save(update_fields=["user"])
        dev_student.user = student_user
        dev_student.save(update_fields=["user"])
        response_dev = self.client.get(reverse("career_twin") + f"?student_id={high_student.id}")
        self.assertEqual(response_dev.status_code, 200)
        self.assertEqual(response_dev.context["student"], dev_student)
        # (50 + 45 + 55 + 50) / 4 = 50
        self.assertEqual(response_dev.context["readiness"], 50)
        self.assertEqual(response_dev.context["readiness_level"], "Needs Skill Development")

    def test_career_twin_skill_gap_calculation(self):
        self.login_as_student()
        response = self.client.get(reverse("career_twin"))
        self.assertEqual(response.status_code, 200)

        # Rahul Kumar has: Python, SQL, Django, HTML, CSS, C
        # TCS requires: Python, SQL, Data Structures, Algorithms, Git, OOPS
        matched_skills = response.context["all_matched_skills"]
        missing_skills = response.context["top_missing_skills"]

        self.assertIn("python", matched_skills)
        self.assertIn("sql", matched_skills)
        self.assertIn("data structures", missing_skills)
        self.assertIn("algorithms", missing_skills)
        self.assertIn("git", missing_skills)
        self.assertIn("oops", missing_skills)

        # Role analysis checks
        role_analysis = response.context["role_analyses"][0]
        self.assertEqual(role_analysis["match_pct"], 33)
        self.assertEqual(len(role_analysis["matched_skills"]), 2)
        self.assertEqual(len(role_analysis["missing_skills"]), 4)

    def test_career_twin_unauthorized_access(self):
        anonymous_response = self.client.get(reverse("career_twin"))
        self.assertEqual(anonymous_response.status_code, 302)
        self.login_as_student()
        response = self.client.get(reverse("career_twin") + "?student_id=99999")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["student"], self.student)

    def test_career_twin_empty_database_graceful(self):
        self.login_as_student()
        Student.objects.all().delete()
        response = self.client.get(reverse("career_twin"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student profile not linked")


class RecruiterPortalTests(TestCase):
    def setUp(self):
        self.client = Client()
        recruiter_group, _ = Group.objects.get_or_create(name="RECRUITER")
        student_group, _ = Group.objects.get_or_create(name="STUDENT")
        self.recruiter = User.objects.create(
            username="recruiter_one", password="unused-test-password"
        )
        self.recruiter.groups.add(recruiter_group)
        self.other_recruiter = User.objects.create(
            username="recruiter_two", password="unused-test-password"
        )
        self.other_recruiter.groups.add(recruiter_group)
        self.student_user = User.objects.create(
            username="student_one", password="unused-test-password"
        )
        self.student_user.groups.add(student_group)
        self.student = Student.objects.create(
            name="Rahul Kumar",
            email="rahul-recruiter-test@example.com",
            phone="9876543210",
            branch="MCA",
            semester=1,
            cgpa=8.20,
            backlogs=0,
            skills="Python, SQL",
            projects="",
            certifications="",
            technical_score=75,
            aptitude_score=72,
            communication_score=68,
            interview_score=70,
        )
        self.owned_job = self.create_job(self.recruiter, "Owned Systems")
        self.other_job = self.create_job(self.other_recruiter, "Other Systems")
        self.application = Application.objects.create(
            student=self.student,
            job=self.owned_job,
        )

    def create_job(self, owner, title):
        return Job.objects.create(
            recruiter=owner,
            company_name="CampusLink Labs",
            job_title=title,
            description="Recruiter workflow test job.",
            required_skills="Python, Java",
            minimum_cgpa=6.0,
            maximum_backlogs=0,
        )

    def test_anonymous_user_is_redirected_from_recruiter_dashboard(self):
        response = self.client.get(reverse("recruiter_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_student_group_is_denied_recruiter_dashboard(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse("recruiter_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_recruiter_cannot_access_student_career_twin(self):
        self.client.force_login(self.recruiter)
        self.assertEqual(self.client.get(reverse("career_twin")).status_code, 403)

    def test_recruiter_group_can_access_dashboard(self):
        self.client.force_login(self.recruiter)
        response = self.client.get(reverse("recruiter_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_jobs"], 1)
        self.assertEqual(response.context["total_applications"], 1)

    def test_recruiter_sees_only_owned_jobs(self):
        self.client.force_login(self.recruiter)
        response = self.client.get(reverse("recruiter_jobs"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Owned Systems")
        self.assertNotContains(response, "Other Systems")
        self.assertEqual(list(response.context["jobs"]), [self.owned_job])

    def test_created_job_ownership_and_status_are_server_assigned(self):
        self.client.force_login(self.recruiter)
        response = self.client.post(reverse("recruiter_job_create"), {
            "company_name": "New Campus Co",
            "job_title": "Backend Engineer",
            "description": "Build services.",
            "required_skills": "Python, Django",
            "minimum_cgpa": "7.00",
            "maximum_backlogs": "0",
            "location": "Bhubaneswar",
            "package": "8 LPA",
            "deadline": "2026-10-15",
            "drive_date": "2026-11-01",
            "status": Job.Status.CLOSED,
            "recruiter": self.other_recruiter.pk,
        })
        self.assertEqual(response.status_code, 302)
        created_job = Job.objects.get(job_title="Backend Engineer")
        self.assertEqual(created_job.recruiter, self.recruiter)
        self.assertEqual(created_job.status, Job.Status.OPEN)
        self.assertEqual(created_job.deadline.isoformat(), "2026-10-15")
        self.assertEqual(created_job.drive_date.isoformat(), "2026-11-01")

    def test_invalid_job_date_is_rejected(self):
        self.client.force_login(self.recruiter)
        response = self.client.post(reverse("recruiter_job_create"), {
            "company_name": "Date Check Co",
            "job_title": "Date Check Role",
            "required_skills": "Python",
            "minimum_cgpa": "6.00",
            "maximum_backlogs": "0",
            "deadline": "not-a-date",
            "drive_date": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(Job.objects.filter(job_title="Date Check Role").exists())

    def test_invalid_job_requirement_ranges_are_rejected(self):
        self.client.force_login(self.recruiter)
        base_data = {
            "company_name": "Range Check Co",
            "required_skills": "Python",
            "maximum_backlogs": "0",
        }
        for title, cgpa, backlogs in (
            ("Too High CGPA", "10.01", "0"),
            ("Negative CGPA", "-0.01", "0"),
            ("Negative Backlogs", "8.00", "-1"),
        ):
            response = self.client.post(reverse("recruiter_job_create"), {
                **base_data,
                "job_title": title,
                "minimum_cgpa": cgpa,
                "maximum_backlogs": backlogs,
            })
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
        self.assertFalse(Job.objects.filter(company_name="Range Check Co").exists())

    def test_get_requests_do_not_mutate_post_only_actions(self):
        self.client.force_login(self.recruiter)
        job_status_url = reverse("recruiter_job_toggle_status", args=[self.owned_job.id])
        application_status_url = reverse(
            "recruiter_application_status", args=[self.application.id]
        )
        self.assertEqual(self.client.get(job_status_url).status_code, 405)
        self.assertEqual(self.client.get(application_status_url).status_code, 405)
        self.owned_job.refresh_from_db()
        self.application.refresh_from_db()
        self.assertEqual(self.owned_job.status, Job.Status.OPEN)
        self.assertEqual(self.application.status, Application.Status.APPLIED)

        student_group, _ = Group.objects.get_or_create(name="STUDENT")
        linked_user = User.objects.create(username="get_mutation_student")
        linked_user.groups.add(student_group)
        self.student.user = linked_user
        self.student.save(update_fields=["user"])
        self.client.force_login(linked_user)
        application_count_before = Application.objects.count()
        self.assertEqual(self.client.get(reverse("apply_to_job", args=[self.owned_job.id])).status_code, 405)
        self.assertEqual(Application.objects.count(), application_count_before)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.APPLIED)

    def test_recruiter_mutations_require_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.recruiter)
        response = csrf_client.post(
            reverse("recruiter_job_toggle_status", args=[self.owned_job.id])
        )
        self.assertEqual(response.status_code, 403)
        self.owned_job.refresh_from_db()
        self.assertEqual(self.owned_job.status, Job.Status.OPEN)
        response = csrf_client.post(
            reverse("recruiter_application_status", args=[self.application.id]),
            {"status": Application.Status.OFFERED},
        )
        self.assertEqual(response.status_code, 403)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.APPLIED)

    def test_recruiter_cannot_edit_another_recruiters_job(self):
        self.client.force_login(self.recruiter)
        response = self.client.get(
            reverse("recruiter_job_edit", args=[self.other_job.id])
        )
        self.assertEqual(response.status_code, 404)

    def test_recruiter_cannot_close_another_recruiters_job(self):
        self.client.force_login(self.recruiter)
        response = self.client.post(
            reverse("recruiter_job_toggle_status", args=[self.other_job.id])
        )
        self.assertEqual(response.status_code, 404)
        self.other_job.refresh_from_db()
        self.assertEqual(self.other_job.status, Job.Status.OPEN)

    def test_recruiter_can_view_applicants_for_owned_job(self):
        self.client.force_login(self.recruiter)
        response = self.client.get(
            reverse("recruiter_applications", args=[self.owned_job.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rahul Kumar")
        self.assertContains(response, "Not recorded")
        self.assertEqual(response.context["applicants"][0]["match_score"], 50)
        self.assertTrue(response.context["applicants"][0]["eligible"])

    def test_recruiter_cannot_view_another_recruiters_applicants(self):
        self.client.force_login(self.recruiter)
        response = self.client.get(
            reverse("recruiter_applications", args=[self.other_job.id])
        )
        self.assertEqual(response.status_code, 404)

    def test_recruiter_cannot_access_unowned_tcs_job(self):
        unowned_tcs = Job.objects.create(
            company_name="TCS",
            job_title="Software Developer",
            required_skills="Python, SQL",
            minimum_cgpa=6.0,
            maximum_backlogs=0,
            recruiter=None,
        )
        tcs_application = Application.objects.create(
            student=self.student,
            job=unowned_tcs,
        )
        self.client.force_login(self.recruiter)
        self.assertEqual(
            self.client.get(reverse("recruiter_job_detail", args=[unowned_tcs.id])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(reverse("recruiter_applications", args=[unowned_tcs.id])).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(reverse("recruiter_job_toggle_status", args=[unowned_tcs.id])).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                reverse("recruiter_application_status", args=[tcs_application.id]),
                {"status": Application.Status.OFFERED},
            ).status_code,
            404,
        )
        unowned_tcs.refresh_from_db()
        tcs_application.refresh_from_db()
        self.assertIsNone(unowned_tcs.recruiter_id)
        self.assertEqual(unowned_tcs.status, Job.Status.OPEN)
        self.assertEqual(tcs_application.status, Application.Status.APPLIED)

    def test_recruiter_can_update_owned_application_status(self):
        self.client.force_login(self.recruiter)
        response = self.client.post(
            reverse("recruiter_application_status", args=[self.application.id]),
            {"status": Application.Status.SHORTLISTED},
        )
        self.assertEqual(response.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.SHORTLISTED)

    def test_recruiter_cannot_update_another_recruiters_application(self):
        other_application = Application.objects.create(
            student=self.student,
            job=self.other_job,
        )
        self.client.force_login(self.recruiter)
        response = self.client.post(
            reverse("recruiter_application_status", args=[other_application.id]),
            {"status": Application.Status.OFFERED},
        )
        self.assertEqual(response.status_code, 404)
        other_application.refresh_from_db()
        self.assertEqual(other_application.status, Application.Status.APPLIED)

    def test_student_cannot_change_application_status(self):
        self.client.force_login(self.student_user)
        response = self.client.post(
            reverse("recruiter_application_status", args=[self.application.id]),
            {"status": Application.Status.OFFERED},
        )
        self.assertEqual(response.status_code, 403)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.APPLIED)

    def test_student_views_and_application_relationship_remain_available(self):
        self.assertEqual(self.student.applications.get(), self.application)
        student_group, _ = Group.objects.get_or_create(name="STUDENT")
        student_user = User.objects.create(
            username="linked_portal_student", password="unused"
        )
        student_user.groups.add(student_group)
        self.student.user = student_user
        self.student.save(update_fields=["user"])
        self.client.force_login(student_user)
        self.assertEqual(self.client.get(reverse("student_dashboard")).status_code, 200)
        self.assertEqual(self.client.get(reverse("career_twin")).status_code, 200)
        self.assertEqual(self.client.get(reverse("job_match", args=[self.owned_job.id])).status_code, 200)
        self.assertEqual(self.client.get(reverse("job_match", args=[999])).status_code, 404)

    def test_invalid_application_status_is_rejected(self):
        self.client.force_login(self.recruiter)
        response = self.client.post(
            reverse("recruiter_application_status", args=[self.application.id]),
            {"status": "HIRED"},
        )
        self.assertEqual(response.status_code, 400)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.APPLIED)

    def test_staff_and_superuser_are_not_recruiters_without_group(self):
        privileged_user = User.objects.create(
            username="privileged_without_recruiter_group",
            password="unused-test-password",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(privileged_user)
        response = self.client.get(reverse("recruiter_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_recruiter_can_close_and_reopen_owned_job(self):
        self.client.force_login(self.recruiter)
        url = reverse("recruiter_job_toggle_status", args=[self.owned_job.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.owned_job.refresh_from_db()
        self.assertEqual(self.owned_job.status, Job.Status.CLOSED)
        self.client.post(url)
        self.owned_job.refresh_from_db()
        self.assertEqual(self.owned_job.status, Job.Status.OPEN)

    def test_empty_dashboard_and_job_list_render_safely(self):
        self.application.delete()
        self.owned_job.delete()
        self.client.force_login(self.recruiter)
        dashboard = self.client.get(reverse("recruiter_dashboard"))
        job_list = self.client.get(reverse("recruiter_jobs"))
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "No jobs yet")
        self.assertEqual(dashboard.context["total_jobs"], 0)
        self.assertEqual(dashboard.context["total_applications"], 0)
        self.assertEqual(job_list.status_code, 200)
        self.assertContains(job_list, "No jobs yet")

    def test_empty_applicant_list_renders_safely(self):
        empty_job = self.create_job(self.recruiter, "No Applicants Yet")
        self.client.force_login(self.recruiter)
        response = self.client.get(
            reverse("recruiter_applications", args=[empty_job.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No applications yet")


class StudentApplicationWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        student_group, _ = Group.objects.get_or_create(name="STUDENT")
        self.student_user = User.objects.create(
            username="workflow_student", password="unused"
        )
        self.student_user.groups.add(student_group)
        self.other_user = User.objects.create(username="other_student", password="unused")
        self.other_user.groups.add(student_group)
        self.student = self.create_student(
            "Linked Student", "linked@example.com", self.student_user
        )
        self.other_student = self.create_student(
            "Other Student", "other@example.com", self.other_user
        )
        self.job = Job.objects.create(
            company_name="Eligible Co",
            job_title="Python Developer",
            description="A role for Python developers.",
            required_skills="Python, Django",
            minimum_cgpa=7.0,
            maximum_backlogs=0,
            status=Job.Status.OPEN,
            deadline=date(2026, 12, 15),
        )
        self.other_job = Job.objects.create(
            company_name="Private Co",
            job_title="Private Role",
            required_skills="Python",
            minimum_cgpa=7.0,
            maximum_backlogs=0,
        )

    def create_student(self, name, email, user=None):
        return Student.objects.create(
            user=user,
            name=name,
            email=email,
            phone="1234567890",
            branch="Computer Science",
            semester=6,
            cgpa=8.5,
            backlogs=0,
            skills="Python, Django, SQL",
            technical_score=80,
            aptitude_score=80,
            communication_score=80,
            interview_score=80,
        )

    def test_anonymous_cannot_access_student_only_application_pages(self):
        self.assertEqual(
            self.client.get(reverse("student_dashboard")).status_code, 302
        )
        self.assertEqual(
            self.client.get(reverse("student_applications")).status_code, 302
        )
        response = self.client.post(reverse("apply_to_job", args=[self.job.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Application.objects.count(), 0)

    def test_non_student_user_cannot_access_application_pages(self):
        ordinary_user = User.objects.create(username="ordinary", password="unused")
        self.client.force_login(ordinary_user)
        self.assertEqual(
            self.client.get(reverse("student_applications")).status_code, 403
        )
        self.assertEqual(
            self.client.get(reverse("student_dashboard")).status_code, 403
        )
        self.assertEqual(
            self.client.post(reverse("apply_to_job", args=[self.job.id])).status_code,
            403,
        )

    def test_student_without_linked_profile_gets_safe_message(self):
        unlinked_user = User.objects.create(username="unlinked_student", password="unused")
        unlinked_user.groups.add(Group.objects.get(name="STUDENT"))
        self.client.force_login(unlinked_user)
        dashboard = self.client.get(reverse("student_dashboard"))
        applications = self.client.get(reverse("student_applications"))
        career_twin = self.client.get(reverse("career_twin"))
        apply_response = self.client.post(
            reverse("apply_to_job", args=[self.job.id])
        )
        for response in (dashboard, applications, career_twin, apply_response):
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Student profile not linked")
        self.assertEqual(Application.objects.count(), 0)

    def test_dashboard_uses_only_authenticated_linked_student(self):
        self.client.force_login(self.student_user)
        response = self.client.get(
            reverse("student_dashboard") + f"?student_id={self.other_student.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["student"], self.student)
        self.assertContains(response, "Linked Student")
        self.assertNotContains(response, "Other Student")

    def test_student_id_query_does_not_select_profile_for_job_match(self):
        self.client.force_login(self.student_user)
        response = self.client.get(
            reverse("job_match", args=[self.job.id])
            + f"?student_id={self.other_student.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["student"], self.student)
        self.assertContains(response, "Linked Student")
        self.assertNotContains(response, "Other Student")

    def test_eligible_student_can_view_job_match(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse("job_match", args=[self.job.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["eligible"])
        self.assertContains(response, "Apply Now")
        self.assertContains(response, "Why This Match Result Exists")

    def test_public_job_detail_does_not_expose_forged_student_profile(self):
        response = self.client.get(
            reverse("job_match", args=[self.job.id])
            + f"?student_id={self.other_student.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["student"])
        self.assertContains(response, "Eligible Co")
        self.assertContains(response, "Student match unavailable")
        self.assertNotContains(response, "Other Student")

    def test_applied_and_closed_states_replace_apply_button(self):
        self.client.force_login(self.student_user)
        Application.objects.create(student=self.student, job=self.job)
        applied_response = self.client.get(reverse("job_match", args=[self.job.id]))
        self.assertContains(applied_response, "Application status:")
        self.assertContains(applied_response, "<strong>Applied</strong>", html=True)
        self.assertNotContains(applied_response, "Apply Now")
        closed_job = Job.objects.create(
            company_name="Closed Co",
            job_title="Closed Python Role",
            required_skills="Python",
            minimum_cgpa=7.0,
            maximum_backlogs=0,
            status=Job.Status.CLOSED,
        )
        closed_response = self.client.get(reverse("job_match", args=[closed_job.id]))
        self.assertContains(closed_response, "This job is closed")
        self.assertNotContains(closed_response, "Apply Now")

    def test_eligible_student_can_apply_using_server_linked_profile(self):
        self.client.force_login(self.student_user)
        response = self.client.post(
            reverse("apply_to_job", args=[self.job.id]),
            {"student": self.other_student.id, "status": Application.Status.OFFERED},
        )
        self.assertEqual(response.status_code, 302)
        application = Application.objects.get(job=self.job)
        self.assertEqual(application.student, self.student)
        self.assertEqual(application.status, Application.Status.APPLIED)

    def test_application_submission_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.student_user)
        response = csrf_client.post(reverse("apply_to_job", args=[self.job.id]))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Application.objects.filter(student=self.student, job=self.job).exists())

    def test_ineligible_student_cannot_apply(self):
        self.job.minimum_cgpa = 9.0
        self.job.save(update_fields=["minimum_cgpa"])
        self.client.force_login(self.student_user)
        response = self.client.post(reverse("apply_to_job", args=[self.job.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Application.objects.filter(student=self.student, job=self.job).exists())
        self.assertContains(self.client.get(response.url), "You are not eligible to apply")

    def test_closed_job_cannot_receive_application(self):
        self.job.status = Job.Status.CLOSED
        self.job.save(update_fields=["status"])
        self.client.force_login(self.student_user)
        response = self.client.post(reverse("apply_to_job", args=[self.job.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Application.objects.filter(student=self.student, job=self.job).exists())
        self.assertContains(self.client.get(response.url), "This job is closed")

    def test_duplicate_application_is_prevented(self):
        existing = Application.objects.create(student=self.student, job=self.job)
        self.client.force_login(self.student_user)
        response = self.client.post(reverse("apply_to_job", args=[self.job.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Application.objects.filter(student=self.student, job=self.job).count(), 1)
        existing.refresh_from_db()
        self.assertEqual(existing.status, Application.Status.APPLIED)
        self.assertContains(self.client.get(response.url), "already applied")

    def test_student_applications_are_scoped_to_linked_profile(self):
        own_application = Application.objects.create(student=self.student, job=self.job)
        Application.objects.create(student=self.other_student, job=self.other_job)
        self.client.force_login(self.student_user)
        response = self.client.get(
            reverse("student_applications") + f"?student_id={self.other_student.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["applications"]), 1)
        self.assertEqual(response.context["applications"][0]["application"], own_application)
        self.assertContains(response, "Eligible Co")
        self.assertNotContains(response, "Private Co")
        self.assertContains(response, "Dec 15, 2026")
        self.assertNotContains(response, 'name="status"')

    def test_student_status_is_read_only(self):
        application = Application.objects.create(student=self.student, job=self.job)
        self.client.force_login(self.student_user)
        response = self.client.post(
            reverse("recruiter_application_status", args=[application.id]),
            {"status": Application.Status.OFFERED},
        )
        self.assertEqual(response.status_code, 403)
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.APPLIED)

    def test_career_twin_uses_linked_student_for_student_group(self):
        self.client.force_login(self.student_user)
        response = self.client.get(
            reverse("career_twin") + f"?student_id={self.other_student.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["student"], self.student)

    def test_user_with_student_and_recruiter_groups_gets_only_those_portals(self):
        recruiter_group, _ = Group.objects.get_or_create(name="RECRUITER")
        self.student_user.groups.add(recruiter_group)
        self.client.force_login(self.student_user)
        self.assertEqual(self.client.get(reverse("student_dashboard")).status_code, 200)
        self.assertEqual(self.client.get(reverse("career_twin")).status_code, 200)
        self.assertEqual(self.client.get(reverse("recruiter_dashboard")).status_code, 200)
        self.assertEqual(self.client.get(reverse("tpo_dashboard")).status_code, 403)

    def test_job_not_found_remains_404(self):
        self.client.force_login(self.student_user)
        self.assertEqual(self.client.get(reverse("job_match", args=[999])).status_code, 404)


class TPOPlacementPortalTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.tpo_group, _ = Group.objects.get_or_create(name="TPO")
        self.student_group, _ = Group.objects.get_or_create(name="STUDENT")
        self.recruiter_group, _ = Group.objects.get_or_create(name="RECRUITER")
        self.tpo_user = User.objects.create(username="placement_officer")
        self.tpo_user.groups.add(self.tpo_group)
        self.student_user = User.objects.create(username="tpo_student_user")
        self.student_user.groups.add(self.student_group)
        self.recruiter_user = User.objects.create(username="tpo_recruiter_user")
        self.recruiter_user.groups.add(self.recruiter_group)

        self.student = self.create_student("Asha Rao", "asha-tpo@example.com", "CSE")
        self.other_student = self.create_student(
            "Ravi Das", "ravi-tpo@example.com", "ECE"
        )
        self.open_job = self.create_job("Open Co", "Developer", Job.Status.OPEN)
        self.closed_job = self.create_job("Closed Co", "Analyst", Job.Status.CLOSED)
        self.applications = [
            Application.objects.create(
                student=self.student, job=self.open_job,
                status=Application.Status.APPLIED,
            ),
            Application.objects.create(
                student=self.student, job=self.closed_job,
                status=Application.Status.SHORTLISTED,
            ),
            Application.objects.create(
                student=self.other_student, job=self.open_job,
                status=Application.Status.REJECTED,
            ),
            Application.objects.create(
                student=self.other_student, job=self.closed_job,
                status=Application.Status.OFFERED,
            ),
        ]

    def create_student(self, name, email, branch):
        return Student.objects.create(
            name=name,
            email=email,
            phone="1234567890",
            branch=branch,
            semester=5,
            cgpa=8.1,
            backlogs=0,
            skills="Python, SQL",
            technical_score=80,
            aptitude_score=70,
            communication_score=75,
            interview_score=75,
        )

    def create_job(self, company, title, status):
        return Job.objects.create(
            company_name=company,
            job_title=title,
            required_skills="Python, Java",
            minimum_cgpa=7.0,
            maximum_backlogs=0,
            status=status,
        )

    def test_anonymous_user_cannot_access_tpo_dashboard(self):
        response = self.client.get(reverse("tpo_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_student_and_recruiter_groups_are_denied_tpo_pages(self):
        for user in (self.student_user, self.recruiter_user):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse("tpo_dashboard")).status_code, 403)
            self.assertEqual(self.client.get(reverse("tpo_students")).status_code, 403)
            self.client.logout()

    def test_staff_superuser_without_tpo_group_is_denied(self):
        privileged_user = User.objects.create(
            username="tpo_privileged_without_group",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(privileged_user)
        self.assertEqual(self.client.get(reverse("tpo_dashboard")).status_code, 403)

    def test_tpo_dashboard_shows_real_placement_statistics(self):
        self.client.force_login(self.tpo_user)
        response = self.client.get(reverse("tpo_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["student_count"], 2)
        self.assertEqual(response.context["job_count"], 2)
        self.assertEqual(response.context["open_job_count"], 1)
        self.assertEqual(response.context["closed_job_count"], 1)
        self.assertEqual(response.context["application_count"], 4)
        self.assertEqual(response.context["applied_count"], 1)
        self.assertEqual(response.context["shortlisted_count"], 1)
        self.assertEqual(response.context["rejected_count"], 1)
        self.assertEqual(response.context["offered_count"], 1)
        self.assertEqual(response.context["students_with_offers"], 1)
        self.assertEqual(response.context["total_offers"], 1)

    def test_tpo_can_view_student_list_and_detail(self):
        self.client.force_login(self.tpo_user)
        response = self.client.get(reverse("tpo_students"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Asha Rao")
        self.assertContains(response, "asha-tpo@example.com")
        detail = self.client.get(reverse("tpo_student_detail", args=[self.student.id]))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.context["student"], self.student)

    def test_tpo_can_view_jobs_and_details_without_ownership_mutation(self):
        self.client.force_login(self.tpo_user)
        response = self.client.get(reverse("tpo_jobs"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Open Co")
        self.assertContains(response, "Closed Co")
        detail = self.client.get(reverse("tpo_job_detail", args=[self.open_job.id]))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.context["job"], self.open_job)

    def test_tpo_can_view_all_applications(self):
        self.client.force_login(self.tpo_user)
        response = self.client.get(reverse("tpo_applications"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["application_rows"]), 4)

    def test_tpo_application_filters_use_database_values(self):
        self.client.force_login(self.tpo_user)
        response = self.client.get(reverse("tpo_applications"), {
            "status": Application.Status.OFFERED,
            "company": "Closed Co",
            "student": str(self.other_student.id),
            "branch": "ECE",
        })
        self.assertEqual(response.status_code, 200)
        rows = response.context["application_rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["application"], self.applications[3])

    def test_tpo_cannot_use_recruiter_mutations_or_student_private_views(self):
        self.client.force_login(self.tpo_user)
        self.assertEqual(
            self.client.post(reverse("recruiter_job_toggle_status", args=[self.open_job.id])).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse("recruiter_application_status", args=[self.applications[0].id]),
                {"status": Application.Status.OFFERED},
            ).status_code,
            403,
        )
        self.assertEqual(self.client.get(reverse("student_dashboard")).status_code, 403)
        self.assertEqual(self.client.get(reverse("student_applications")).status_code, 403)
        self.assertEqual(self.client.get(reverse("career_twin")).status_code, 403)
        self.assertEqual(
            self.client.post(reverse("apply_to_job", args=[self.open_job.id])).status_code,
            403,
        )
        self.applications[0].refresh_from_db()
        self.assertEqual(self.applications[0].status, Application.Status.APPLIED)

    def test_tpo_analytics_requires_authentication_and_tpo_group(self):
        url = reverse("tpo_analytics")
        self.assertEqual(self.client.get(url).status_code, 302)
        for user in (self.student_user, self.recruiter_user):
            self.client.force_login(user)
            self.assertEqual(self.client.get(url).status_code, 403)
            self.client.logout()
        privileged_user = User.objects.create(
            username="analytics_admin_without_tpo",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(privileged_user)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_tpo_analytics_reports_real_student_job_and_application_metrics(self):
        self.open_job.deadline = date(2026, 12, 1)
        self.open_job.drive_date = date(2026, 12, 10)
        self.open_job.save(update_fields=["deadline", "drive_date"])
        second_offer_job = self.create_job(
            "Second Offer Co", "Second Role", Job.Status.CLOSED
        )
        Application.objects.create(
            student=self.other_student,
            job=second_offer_job,
            status=Application.Status.OFFERED,
        )
        self.client.force_login(self.tpo_user)
        response = self.client.get(reverse("tpo_analytics"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/tpo_analytics.html")
        self.assertEqual(response.context["total_students"], 2)
        self.assertEqual(response.context["students_with_applications"], 2)
        self.assertEqual(response.context["students_without_applications"], 0)
        self.assertEqual(response.context["students_shortlisted"], 1)
        self.assertEqual(response.context["students_rejected"], 1)
        self.assertEqual(response.context["students_with_offers"], 1)
        self.assertEqual(response.context["application_rate"], 100)
        self.assertEqual(response.context["offer_rate_applicants"], 50)
        self.assertEqual(response.context["offer_rate_all_students"], 50)
        self.assertEqual(response.context["total_jobs"], 3)
        self.assertEqual(response.context["open_jobs"], 1)
        self.assertEqual(response.context["closed_jobs"], 2)
        self.assertEqual(response.context["companies_represented"], 3)
        self.assertEqual(response.context["jobs_with_deadlines"], 1)
        self.assertEqual(response.context["jobs_with_drive_dates"], 1)
        self.assertEqual(response.context["total_applications"], 5)
        self.assertEqual(response.context["offered_applications"], 2)
        self.assertEqual(response.context["students_with_offers"], 1)
        funnel_counts = {
            item["value"]: item["count"]
            for item in response.context["application_funnel"]
        }
        self.assertEqual(funnel_counts[Application.Status.APPLIED], 1)
        self.assertEqual(funnel_counts[Application.Status.SHORTLISTED], 1)
        self.assertEqual(funnel_counts[Application.Status.REJECTED], 1)
        self.assertEqual(funnel_counts[Application.Status.OFFERED], 2)
        self.assertEqual(response.context["evaluated_pairs"], 6)
        self.assertEqual(response.context["average_match_score"], 50)
        self.assertEqual(response.context["eligible_matches"], 6)
        self.assertEqual(response.context["average_readiness"], 75)
        self.assertEqual(response.context["students_needing_improvement"], 0)

    def test_skill_demand_counts_exact_normalized_job_skills(self):
        self.open_job.required_skills = " Python, python, Django "
        self.open_job.save(update_fields=["required_skills"])
        self.closed_job.required_skills = "Java, Django"
        self.closed_job.save(update_fields=["required_skills"])
        self.client.force_login(self.tpo_user)
        response = self.client.get(reverse("tpo_analytics"))
        rows = {
            row["skill"].casefold(): row["job_count"]
            for row in response.context["top_required_skills"]
        }
        self.assertEqual(rows["python"], 1)
        self.assertEqual(rows["django"], 2)
        self.assertEqual(rows["java"], 1)
        self.assertNotIn("flask", rows)

    def test_tpo_analytics_uses_existing_skill_gaps_and_branch_metrics(self):
        self.client.force_login(self.tpo_user)
        response = self.client.get(reverse("tpo_analytics"))
        self.assertTrue(response.context["skill_gap_is_aggregate"])
        gap_rows = {
            row["skill"]: row["pair_count"]
            for row in response.context["frequent_skill_gaps"]
        }
        self.assertEqual(gap_rows["java"], 4)
        branches = {row["branch"]: row for row in response.context["branch_analysis"]}
        self.assertEqual(branches["CSE"]["student_count"], 1)
        self.assertEqual(branches["CSE"]["average_cgpa"], Decimal("8.10"))
        self.assertEqual(branches["CSE"]["application_count"], 2)
        self.assertEqual(branches["ECE"]["offer_count"], 1)
        companies = {row["company_name"]: row for row in response.context["company_analysis"]}
        self.assertEqual(companies["Open Co"]["application_count"], 2)
        self.assertEqual(companies["Closed Co"]["offer_count"], 1)

    def test_empty_analytics_state_is_safe_and_explicit(self):
        Application.objects.all().delete()
        Student.objects.all().delete()
        Job.objects.all().delete()
        self.client.force_login(self.tpo_user)
        response = self.client.get(reverse("tpo_analytics"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["application_rate"], 0)
        self.assertEqual(response.context["offer_rate_applicants"], 0)
        self.assertEqual(response.context["offer_rate_all_students"], 0)
        self.assertEqual(response.context["average_match_score"], 0)
        self.assertContains(response, "No application data available yet.")
        self.assertContains(response, "No job skill requirements are available yet.")
        self.assertContains(response, "No student/job pairs are available for matching analysis.")

    def test_single_student_job_gap_summary_is_marked_insufficient(self):
        Application.objects.all().delete()
        self.other_student.delete()
        self.closed_job.delete()
        self.client.force_login(self.tpo_user)
        response = self.client.get(reverse("tpo_analytics"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["skill_gap_is_aggregate"])
        self.assertFalse(response.context["match_is_aggregate"])
        self.assertContains(response, "Insufficient data for aggregate analysis")
        self.assertContains(response, "Insufficient data for aggregate match analysis")

    def test_optional_blank_student_values_do_not_crash_analytics(self):
        self.student.branch = ""
        self.student.skills = ""
        self.student.save(update_fields=["branch", "skills"])
        self.open_job.required_skills = ""
        self.open_job.save(update_fields=["required_skills"])
        self.client.force_login(self.tpo_user)
        response = self.client.get(reverse("tpo_analytics"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(
            row["branch"] == "Not specified"
            for row in response.context["branch_analysis"]
        ))


class DemoSeedCommandTests(TestCase):
    def setUp(self):
        self.existing_user = User.objects.create_user(
            username="unrelated_existing_user",
            email="existing@example.com",
            password="existing-safe-password",
        )
        unrelated_group, _ = Group.objects.get_or_create(name="UNRELATED")
        self.existing_user.groups.add(unrelated_group)
        self.rahul = Student.objects.create(
            name="Rahul Kumar",
            email="rahul-existing@example.com",
            phone="9876543210",
            branch="MCA",
            semester=1,
            cgpa="8.20",
            backlogs=0,
            technical_score=75,
            aptitude_score=72,
            communication_score=68,
            interview_score=70,
            skills="Python, SQL, Django",
            projects="Existing project",
            certifications="Existing certificate",
        )
        self.tcs = Job.objects.create(
            company_name="TCS",
            job_title="Software Developer",
            description="Existing TCS description.",
            required_skills="Python, SQL",
            minimum_cgpa="6.00",
            maximum_backlogs=0,
            location="Bhubaneswar",
            package="5 LPA",
            status=Job.Status.OPEN,
        )
        self.rahul_snapshot = dict(
            Student.objects.filter(pk=self.rahul.pk).values().get()
        )
        self.tcs_snapshot = dict(Job.objects.filter(pk=self.tcs.pk).values().get())

    def run_seed(self):
        output = StringIO()
        call_command("seed_demo_data", stdout=output, no_color=True)
        return output.getvalue()

    def test_seed_creates_demo_records_users_links_groups_and_applications(self):
        output = self.run_seed()
        self.assertEqual(
            Student.objects.filter(email__startswith="demo.student").count(), 10
        )
        self.assertEqual(
            Job.objects.filter(company_name__startswith="Demo Company").count(), 8
        )
        self.assertEqual(
            User.objects.filter(username__startswith="demo_").count(), 13
        )
        for user in User.objects.filter(username__startswith="demo_"):
            self.assertTrue(user.check_password(DEMO_PASSWORD))
            self.assertNotEqual(user.password, DEMO_PASSWORD)
        demo_applications = Application.objects.filter(
            student__email__startswith="demo.student",
            job__company_name__startswith="Demo Company",
        )
        self.assertGreaterEqual(demo_applications.count(), 4)
        self.assertEqual(
            set(demo_applications.values_list("status", flat=True)),
            set(Application.Status.values),
        )
        for index in range(1, 11):
            student = Student.objects.get(
                email=f"demo.student{index:02d}@campuslink.local"
            )
            self.assertEqual(student.user.username, f"demo_student{index:02d}")
            self.assertEqual(list(student.user.groups.values_list("name", flat=True)), ["STUDENT"])
        for username in ("demo_recruiter01", "demo_recruiter02"):
            recruiter = User.objects.get(username=username)
            self.assertEqual(
                list(recruiter.groups.values_list("name", flat=True)),
                ["RECRUITER"],
            )
        demo_tpo = User.objects.get(username="demo_tpo")
        self.assertEqual(list(demo_tpo.groups.values_list("name", flat=True)), ["TPO"])
        demo_jobs = Job.objects.filter(company_name__startswith="Demo Company")
        self.assertTrue(demo_jobs.exists())
        self.assertEqual(
            set(demo_jobs.values_list("recruiter__username", flat=True)),
            {"demo_recruiter01", "demo_recruiter02"},
        )
        self.assertIn("Applications created:", output)

    def test_seed_is_repeatable_and_preserves_unrelated_records(self):
        self.run_seed()
        first_counts = {
            "users": User.objects.count(),
            "students": Student.objects.count(),
            "jobs": Job.objects.count(),
            "applications": Application.objects.count(),
        }
        second_output = self.run_seed()
        second_counts = {
            "users": User.objects.count(),
            "students": Student.objects.count(),
            "jobs": Job.objects.count(),
            "applications": Application.objects.count(),
        }
        self.assertEqual(first_counts, second_counts)
        self.assertIn("Students created: 0", second_output)
        self.assertIn("Jobs created: 0", second_output)
        self.assertIn("Applications created: 0", second_output)
        self.assertEqual(dict(Student.objects.filter(pk=self.rahul.pk).values().get()), self.rahul_snapshot)
        self.assertEqual(dict(Job.objects.filter(pk=self.tcs.pk).values().get()), self.tcs_snapshot)
        self.assertEqual(self.rahul.user_id, None)
        self.assertIsNone(self.tcs.recruiter_id)
        self.assertEqual(self.tcs.status, Job.Status.OPEN)
        self.assertEqual(
            list(self.existing_user.groups.values_list("name", flat=True)),
            ["UNRELATED"],
        )

    def test_seed_aborts_before_writing_when_demo_identifier_is_unrelated(self):
        User.objects.create_user(
            username="demo_student01",
            email="someone-else@example.com",
            password="unrelated-safe-password",
        )
        counts_before = (User.objects.count(), Student.objects.count(), Job.objects.count())
        with self.assertRaises(CommandError):
            self.run_seed()
        self.assertEqual(
            (User.objects.count(), Student.objects.count(), Job.objects.count()),
            counts_before,
        )
        self.assertEqual(Student.objects.count(), 1)
        self.assertEqual(Job.objects.count(), 1)

    def test_seeded_student_recruiter_and_tpo_workflows_end_to_end(self):
        self.run_seed()
        demo_students = Student.objects.filter(
            email__startswith="demo.student"
        ).select_related("user")
        apply_target = None
        for student in demo_students:
            for job in Job.objects.filter(status=Job.Status.OPEN):
                if (
                    evaluate_job(student, job)["eligible"]
                    and not Application.objects.filter(student=student, job=job).exists()
                ):
                    apply_target = (student, job)
                    break
            if apply_target:
                break
        self.assertIsNotNone(apply_target)
        student, job = apply_target

        student_client = Client()
        self.assertTrue(student_client.login(
            username=student.user.username, password=DEMO_PASSWORD
        ))
        self.assertEqual(student_client.get(reverse("student_dashboard")).status_code, 200)
        detail = student_client.get(reverse("job_match", args=[job.id]))
        self.assertEqual(detail.status_code, 200)
        self.assertTrue(detail.context["eligible"])
        apply_response = student_client.post(reverse("apply_to_job", args=[job.id]))
        self.assertEqual(apply_response.status_code, 302)
        self.assertTrue(Application.objects.filter(
            student=student, job=job, status=Application.Status.APPLIED
        ).exists())
        self.assertEqual(student_client.get(reverse("student_applications")).status_code, 200)

        recruiter_application = Application.objects.filter(
            job__recruiter__username__startswith="demo_recruiter"
        ).select_related("job", "job__recruiter").first()
        self.assertIsNotNone(recruiter_application)
        recruiter_client = Client()
        recruiter_user = recruiter_application.job.recruiter
        self.assertTrue(recruiter_client.login(
            username=recruiter_user.username, password=DEMO_PASSWORD
        ))
        self.assertEqual(recruiter_client.get(reverse("recruiter_dashboard")).status_code, 200)
        self.assertEqual(recruiter_client.get(reverse("recruiter_jobs")).status_code, 200)
        self.assertEqual(recruiter_client.get(reverse(
            "recruiter_applications", args=[recruiter_application.job_id]
        )).status_code, 200)
        update_response = recruiter_client.post(
            reverse("recruiter_application_status", args=[recruiter_application.id]),
            {"status": Application.Status.SHORTLISTED},
        )
        self.assertEqual(update_response.status_code, 302)
        recruiter_application.refresh_from_db()
        self.assertEqual(recruiter_application.status, Application.Status.SHORTLISTED)

        tpo_client = Client()
        tpo_user = User.objects.get(username="demo_tpo")
        self.assertTrue(tpo_client.login(username=tpo_user.username, password=DEMO_PASSWORD))
        for route_name in (
            "tpo_dashboard", "tpo_students", "tpo_jobs", "tpo_applications", "tpo_analytics",
        ):
            self.assertEqual(tpo_client.get(reverse(route_name)).status_code, 200)
        self.assertEqual(student_client.get(reverse("job_match", args=[1])).status_code, 200)
        self.assertEqual(student_client.get(reverse("job_match", args=[999])).status_code, 404)


class PresentationIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def create_role_user(self, username, group_name):
        group, _ = Group.objects.get_or_create(name=group_name)
        user = User.objects.create(username=username)
        user.groups.add(group)
        return user

    def test_home_navigation_is_role_specific(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Intelligent Campus Placement Platform")
        self.assertContains(response, "Explore CAMPUSLINK")
        self.assertContains(response, "Sign in")
        self.assertNotContains(response, reverse("recruiter_dashboard"))
        self.assertNotContains(response, reverse("tpo_dashboard"))

        role_destinations = {
            "STUDENT": ("student_dashboard", "career_twin", "student_applications"),
            "RECRUITER": ("recruiter_dashboard", "recruiter_jobs"),
            "TPO": ("tpo_dashboard", "tpo_students", "tpo_jobs", "tpo_applications", "tpo_analytics"),
        }
        for index, (group_name, names) in enumerate(role_destinations.items()):
            user = self.create_role_user(f"nav_{group_name.lower()}", group_name)
            self.client.force_login(user)
            response = self.client.get(reverse("home"))
            for route_name in names:
                self.assertContains(response, reverse(route_name))
            other_names = {
                "STUDENT": {"recruiter_dashboard", "tpo_dashboard", "tpo_analytics"},
                "RECRUITER": {"student_dashboard", "career_twin", "student_applications", "tpo_dashboard", "tpo_analytics"},
                "TPO": {"student_dashboard", "career_twin", "student_applications", "recruiter_dashboard", "recruiter_jobs"},
            }[group_name]
            for route_name in other_names:
                self.assertNotContains(response, reverse(route_name))

    def test_login_and_post_logout_work(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/login.html")
        user = User.objects.create_user(username="presentation_login", password="safe-login-password")
        response = self.client.post(reverse("login"), {
            "username": user.username,
            "password": "safe-login-password",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        logout_response = self.client.post(reverse("logout"))
        self.assertEqual(logout_response.status_code, 302)
        self.assertFalse(logout_response.wsgi_request.user.is_authenticated)

    @override_settings(DEBUG=False)
    def test_job_404_uses_branded_page_and_preserves_status(self):
        response = self.client.get(reverse("job_match", args=[999]))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "core/404.html")
        self.assertContains(response, "Page not found", status_code=404)
