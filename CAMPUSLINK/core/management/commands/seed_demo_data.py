from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.core.management import BaseCommand, CommandError
from django.db import transaction

from core.matching import evaluate_job
from core.models import Application, Job, Student


User = get_user_model()
DEMO_PASSWORD = "CampusLinkDemo!2026"
APPLICATION_TARGET = 20
APPLICATION_STATUSES = (
    Application.Status.APPLIED,
    Application.Status.SHORTLISTED,
    Application.Status.REJECTED,
    Application.Status.OFFERED,
)

DEMO_USERS = [
    {
        "key": "student01", "username": "demo_student01",
        "email": "demo.student01@campuslink.local", "first_name": "Demo",
        "last_name": "Student 01", "group": "STUDENT",
    },
    {
        "key": "student02", "username": "demo_student02",
        "email": "demo.student02@campuslink.local", "first_name": "Demo",
        "last_name": "Student 02", "group": "STUDENT",
    },
    {
        "key": "student03", "username": "demo_student03",
        "email": "demo.student03@campuslink.local", "first_name": "Demo",
        "last_name": "Student 03", "group": "STUDENT",
    },
    {
        "key": "student04", "username": "demo_student04",
        "email": "demo.student04@campuslink.local", "first_name": "Demo",
        "last_name": "Student 04", "group": "STUDENT",
    },
    {
        "key": "student05", "username": "demo_student05",
        "email": "demo.student05@campuslink.local", "first_name": "Demo",
        "last_name": "Student 05", "group": "STUDENT",
    },
    {
        "key": "student06", "username": "demo_student06",
        "email": "demo.student06@campuslink.local", "first_name": "Demo",
        "last_name": "Student 06", "group": "STUDENT",
    },
    {
        "key": "student07", "username": "demo_student07",
        "email": "demo.student07@campuslink.local", "first_name": "Demo",
        "last_name": "Student 07", "group": "STUDENT",
    },
    {
        "key": "student08", "username": "demo_student08",
        "email": "demo.student08@campuslink.local", "first_name": "Demo",
        "last_name": "Student 08", "group": "STUDENT",
    },
    {
        "key": "student09", "username": "demo_student09",
        "email": "demo.student09@campuslink.local", "first_name": "Demo",
        "last_name": "Student 09", "group": "STUDENT",
    },
    {
        "key": "student10", "username": "demo_student10",
        "email": "demo.student10@campuslink.local", "first_name": "Demo",
        "last_name": "Student 10", "group": "STUDENT",
    },
    {
        "key": "recruiter01", "username": "demo_recruiter01",
        "email": "demo.recruiter01@campuslink.local", "first_name": "Demo",
        "last_name": "Recruiter 01", "group": "RECRUITER",
    },
    {
        "key": "recruiter02", "username": "demo_recruiter02",
        "email": "demo.recruiter02@campuslink.local", "first_name": "Demo",
        "last_name": "Recruiter 02", "group": "RECRUITER",
    },
    {
        "key": "tpo", "username": "demo_tpo",
        "email": "demo.tpo@campuslink.local", "first_name": "Demo",
        "last_name": "TPO", "group": "TPO",
    },
]

DEMO_STUDENTS = [
    {
        "name": "Demo Student 01", "email": "demo.student01@campuslink.local",
        "branch": "Computer Science", "semester": 7, "cgpa": "8.80", "backlogs": 0,
        "skills": "Python, SQL, Django, Git", "projects": "Campus Event Scheduler",
        "certifications": "Python Foundations", "scores": (88, 84, 82, 86),
    },
    {
        "name": "Demo Student 02", "email": "demo.student02@campuslink.local",
        "branch": "Information Technology", "semester": 6, "cgpa": "8.10", "backlogs": 0,
        "skills": "Java, SQL, Spring, Git, Spring Boot", "projects": "Inventory Service",
        "certifications": "Java Associate Preparation", "scores": (80, 78, 82, 79),
    },
    {
        "name": "Demo Student 03", "email": "demo.student03@campuslink.local",
        "branch": "Computer Science", "semester": 8, "cgpa": "7.60", "backlogs": 0,
        "skills": "C++, Data Structures, Algorithms, Git", "projects": "Pathfinding Visualizer",
        "certifications": "", "scores": (82, 74, 70, 76),
    },
    {
        "name": "Demo Student 04", "email": "demo.student04@campuslink.local",
        "branch": "Data Science", "semester": 6, "cgpa": "8.45", "backlogs": 0,
        "skills": "Python, Pandas, NumPy, SQL", "projects": "Transit Demand Analysis",
        "certifications": "Data Analysis Essentials", "scores": (91, 86, 84, 88),
    },
    {
        "name": "Demo Student 05", "email": "demo.student05@campuslink.local",
        "branch": "Electronics", "semester": 7, "cgpa": "7.20", "backlogs": 1,
        "skills": "JavaScript, HTML, CSS, React", "projects": "Accessible Campus Map",
        "certifications": "Web Accessibility Basics", "scores": (76, 73, 88, 78),
    },
    {
        "name": "Demo Student 06", "email": "demo.student06@campuslink.local",
        "branch": "Computer Science", "semester": 8, "cgpa": "8.25", "backlogs": 0,
        "skills": "Python, SQL, Django, REST API, PostgreSQL, Git", "projects": "Study Group API",
        "certifications": "REST API Design", "scores": (90, 82, 76, 84),
    },
    {
        "name": "Demo Student 07", "email": "demo.student07@campuslink.local",
        "branch": "Information Technology", "semester": 7, "cgpa": "7.85", "backlogs": 0,
        "skills": "Java, Spring Boot, REST API, MySQL", "projects": "Transit Ticketing Backend",
        "certifications": "", "scores": (83, 79, 81, 80),
    },
    {
        "name": "Demo Student 08", "email": "demo.student08@campuslink.local",
        "branch": "Business Analytics", "semester": 5, "cgpa": "6.95", "backlogs": 1,
        "skills": "SQL, Excel, Python, Data Analysis", "projects": "Retail Sales Workbook",
        "certifications": "Spreadsheet Analytics", "scores": (72, 88, 85, 74),
    },
    {
        "name": "Demo Student 09", "email": "demo.student09@campuslink.local",
        "branch": "Electronics", "semester": 8, "cgpa": "8.65", "backlogs": 0,
        "skills": "JavaScript, React, TypeScript, CSS", "projects": "Component Library",
        "certifications": "Frontend Testing Basics", "scores": (87, 80, 86, 84),
    },
    {
        "name": "Demo Student 10", "email": "demo.student10@campuslink.local",
        "branch": "Mechanical", "semester": 6, "cgpa": "7.45", "backlogs": 0,
        "skills": "Python, Linux, Git, Data Structures", "projects": "Sensor Log Analyzer",
        "certifications": "Linux Command Line", "scores": (78, 76, 71, 74),
    },
]

DEMO_JOBS = [
    {
        "company": "Demo Company 01", "title": "Demo Job 01 - Software Developer",
        "recruiter": "recruiter01", "skills": "Python, SQL, Django, Git",
        "minimum_cgpa": "6.50", "maximum_backlogs": 1, "location": "Bhubaneswar",
        "package": "6 LPA", "status": Job.Status.OPEN,
        "deadline": date(2026, 11, 20), "drive_date": date(2026, 12, 5),
        "description": "Fictional entry-level software role for the CAMPUSLINK demo.",
    },
    {
        "company": "Demo Company 02", "title": "Demo Job 02 - Java Developer",
        "recruiter": "recruiter01", "skills": "Java, SQL, Spring, Git",
        "minimum_cgpa": "7.00", "maximum_backlogs": 0, "location": "Cuttack",
        "package": "7.5 LPA", "status": Job.Status.OPEN,
        "deadline": date(2026, 11, 25), "drive_date": date(2026, 12, 10),
        "description": "Fictional Java services role for the CAMPUSLINK demo.",
    },
    {
        "company": "Demo Company 03", "title": "Demo Job 03 - Data Analyst",
        "recruiter": "recruiter02", "skills": "Python, SQL, Pandas, Excel",
        "minimum_cgpa": "6.50", "maximum_backlogs": 1, "location": "Remote",
        "package": "6.8 LPA", "status": Job.Status.OPEN,
        "deadline": date(2026, 12, 1), "drive_date": date(2026, 12, 16),
        "description": "Fictional analyst role focused on data preparation and reporting.",
    },
    {
        "company": "Demo Company 04", "title": "Demo Job 04 - Web Developer",
        "recruiter": "recruiter02", "skills": "HTML, CSS, JavaScript, React",
        "minimum_cgpa": "6.50", "maximum_backlogs": 1, "location": "Bhubaneswar",
        "package": "5.8 LPA", "status": Job.Status.OPEN,
        "deadline": date(2026, 12, 3), "drive_date": date(2026, 12, 18),
        "description": "Fictional frontend role for accessible web interfaces.",
    },
    {
        "company": "Demo Company 05", "title": "Demo Job 05 - Backend Developer",
        "recruiter": "recruiter01", "skills": "Python, Django, REST API, PostgreSQL",
        "minimum_cgpa": "7.50", "maximum_backlogs": 0, "location": "Bengaluru",
        "package": "8 LPA", "status": Job.Status.OPEN,
        "deadline": date(2026, 12, 7), "drive_date": date(2026, 12, 22),
        "description": "Fictional backend role building REST services and data stores.",
    },
    {
        "company": "Demo Company 04", "title": "Demo Job 06 - Frontend Developer",
        "recruiter": "recruiter02", "skills": "JavaScript, React, CSS, HTML",
        "minimum_cgpa": "7.00", "maximum_backlogs": 1, "location": "Remote",
        "package": "7 LPA", "status": Job.Status.OPEN,
        "deadline": date(2026, 12, 10), "drive_date": date(2027, 1, 5),
        "description": "Fictional UI engineering role for the CAMPUSLINK demo.",
    },
    {
        "company": "Demo Company 06", "title": "Demo Job 07 - Systems Developer",
        "recruiter": "recruiter01", "skills": "C++, Data Structures, Algorithms, Git",
        "minimum_cgpa": "7.00", "maximum_backlogs": 0, "location": "Rourkela",
        "package": "7.2 LPA", "status": Job.Status.OPEN,
        "deadline": date(2026, 12, 12), "drive_date": date(2027, 1, 8),
        "description": "Fictional systems role for algorithmic problem solving.",
    },
    {
        "company": "Demo Company 03", "title": "Demo Job 08 - Junior Data Scientist",
        "recruiter": "recruiter02", "skills": "Python, NumPy, Pandas, Machine Learning",
        "minimum_cgpa": "8.00", "maximum_backlogs": 0, "location": "Bengaluru",
        "package": "9 LPA", "status": Job.Status.CLOSED,
        "deadline": date(2026, 12, 15), "drive_date": date(2027, 1, 12),
        "description": "Fictional junior data science role; this demo opening is closed.",
    },
]


class Command(BaseCommand):
    help = "Create repeatable, isolated fictional CAMPUSLINK demo data."

    def handle(self, *args, **options):
        before_counts = self._counts()
        self._validate_collisions()
        created = {"users": 0, "students": 0, "jobs": 0, "applications": 0}

        with transaction.atomic():
            demo_password_hash = make_password(DEMO_PASSWORD)
            groups = {
                name: Group.objects.get_or_create(name=name)[0]
                for name in ("STUDENT", "RECRUITER", "TPO")
            }
            users = {}
            for spec in DEMO_USERS:
                user, was_created = self._get_or_create_demo_user(
                    spec, demo_password_hash
                )
                if was_created:
                    created["users"] += 1
                group = groups[spec["group"]]
                if not user.groups.filter(pk=group.pk).exists():
                    user.groups.add(group)
                users[spec["key"]] = user

            students = []
            for index, spec in enumerate(DEMO_STUDENTS, start=1):
                values = {
                    "user": users[f"student{index:02d}"],
                    "name": spec["name"],
                    "email": spec["email"],
                    "phone": f"70000000{index:02d}",
                    "branch": spec["branch"],
                    "semester": spec["semester"],
                    "cgpa": spec["cgpa"],
                    "backlogs": spec["backlogs"],
                    "technical_score": spec["scores"][0],
                    "aptitude_score": spec["scores"][1],
                    "communication_score": spec["scores"][2],
                    "interview_score": spec["scores"][3],
                    "skills": spec["skills"],
                    "projects": spec["projects"],
                    "certifications": spec["certifications"],
                }
                student, was_created = Student.objects.get_or_create(
                    email=spec["email"], defaults=values
                )
                if was_created:
                    created["students"] += 1
                student.refresh_from_db()
                students.append(student)

            jobs = []
            for index, spec in enumerate(DEMO_JOBS, start=1):
                marker = f"[CAMPUSLINK_DEMO:PHASE10:JOB{index:02d}]"
                description = f"{spec['description']}\n\n{marker}"
                values = {
                    "recruiter": users[spec["recruiter"]],
                    "description": description,
                    "required_skills": spec["skills"],
                    "minimum_cgpa": spec["minimum_cgpa"],
                    "maximum_backlogs": spec["maximum_backlogs"],
                    "location": spec["location"],
                    "package": spec["package"],
                    "status": spec["status"],
                    "deadline": spec["deadline"],
                    "drive_date": spec["drive_date"],
                }
                job, was_created = Job.objects.get_or_create(
                    company_name=spec["company"],
                    job_title=spec["title"],
                    defaults=values,
                )
                if was_created:
                    created["jobs"] += 1
                job.refresh_from_db()
                jobs.append(job)

            eligible_pairs = [
                (student, job)
                for student in students
                for job in jobs
                if job.status == Job.Status.OPEN
                and evaluate_job(student, job)["eligible"]
            ]
            for index, (student, job) in enumerate(eligible_pairs[:APPLICATION_TARGET]):
                _application, was_created = Application.objects.get_or_create(
                    student=student,
                    job=job,
                    defaults={"status": APPLICATION_STATUSES[index % len(APPLICATION_STATUSES)]},
                )
                if was_created:
                    created["applications"] += 1

        demo_student_ids = [student.id for student in students]
        demo_job_ids = [job.id for job in jobs]
        demo_applications = Application.objects.filter(
            student_id__in=demo_student_ids,
            job_id__in=demo_job_ids,
        )
        status_counts = {
            status: demo_applications.filter(status=status).count()
            for status in APPLICATION_STATUSES
        }
        after_counts = self._counts()

        self.stdout.write(self.style.SUCCESS("CAMPUSLINK DEMO DATA"))
        self.stdout.write(f"Students created: {created['students']}")
        self.stdout.write(f"Jobs created: {created['jobs']}")
        self.stdout.write(f"Applications created: {created['applications']}")
        for status in APPLICATION_STATUSES:
            self.stdout.write(f"{status}: {status_counts[status]}")
        self.stdout.write(f"Demo users created: {created['users']}")
        self.stdout.write("Demo accounts: demo_student01..10, demo_recruiter01..02, demo_tpo")
        self.stdout.write(f"Local demo password (all demo accounts): {DEMO_PASSWORD}")
        self.stdout.write("Existing records preserved: Rahul Kumar; TCS Software Developer")
        self.stdout.write(f"Counts before: {before_counts}")
        self.stdout.write(f"Counts after:  {after_counts}")
        self.stdout.write("No existing non-demo records were updated or deleted.")

    def _counts(self):
        return {
            "users": User.objects.count(),
            "students": Student.objects.count(),
            "jobs": Job.objects.count(),
            "applications": Application.objects.count(),
        }

    def _validate_collisions(self):
        users_by_key = {}
        for spec in DEMO_USERS:
            user = User.objects.filter(username=spec["username"]).first()
            if user and (
                user.email != spec["email"]
                or user.first_name != spec["first_name"]
                or user.last_name != spec["last_name"]
                or user.is_staff
                or user.is_superuser
            ):
                raise CommandError(
                    f"Username {spec['username']} already belongs to a non-demo account; no data was changed."
                )
            if user:
                existing_groups = set(user.groups.values_list("name", flat=True))
                if existing_groups != {spec["group"]}:
                    raise CommandError(
                        f"Demo account {spec['username']} does not have its exact intended group; no data was changed."
                    )
            users_by_key[spec["key"]] = user

        for index, spec in enumerate(DEMO_STUDENTS, start=1):
            existing = Student.objects.filter(email=spec["email"]).first()
            expected_user = users_by_key[f"student{index:02d}"]
            if existing and (
                expected_user is None
                or existing.name != spec["name"]
                or existing.user_id != expected_user.pk
            ):
                raise CommandError(
                    f"Student identifier {spec['email']} is occupied by an unrelated record; no data was changed."
                )

        for index, spec in enumerate(DEMO_JOBS, start=1):
            existing = Job.objects.filter(
                company_name=spec["company"], job_title=spec["title"]
            ).first()
            marker = f"[CAMPUSLINK_DEMO:PHASE10:JOB{index:02d}]"
            expected_recruiter = users_by_key[spec["recruiter"]]
            if existing and (
                marker not in existing.description
                or expected_recruiter is None
                or existing.recruiter_id != expected_recruiter.pk
            ):
                raise CommandError(
                    f"Job identifier {spec['company']} / {spec['title']} is occupied by an unrelated record; no data was changed."
                )

    def _get_or_create_demo_user(self, spec, password_hash):
        user = User.objects.filter(username=spec["username"]).first()
        if user:
            return user, False
        user = User.objects.create_user(
            username=spec["username"],
            email=spec["email"],
            first_name=spec["first_name"],
            last_name=spec["last_name"],
            password=None,
            is_staff=False,
            is_superuser=False,
        )
        user.password = password_hash
        user.save(update_fields=["password"])
        return user, True
