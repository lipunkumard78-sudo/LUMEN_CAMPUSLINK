from django.conf import settings
from django.db import models


class Student(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_profile",
    )

    # =========================
    # BASIC STUDENT INFORMATION
    # =========================

    name = models.CharField(max_length=100)

    email = models.EmailField(unique=True)

    phone = models.CharField(max_length=15)

    branch = models.CharField(max_length=100)

    semester = models.IntegerField()


    # =========================
    # ACADEMIC INFORMATION
    # =========================

    cgpa = models.DecimalField(
        max_digits=4,
        decimal_places=2
    )

    backlogs = models.IntegerField(
        default=0
    )


    # =========================
    # READINESS ASSESSMENT
    # =========================

    technical_score = models.IntegerField(
        default=0
    )

    aptitude_score = models.IntegerField(
        default=0
    )

    communication_score = models.IntegerField(
        default=0
    )

    interview_score = models.IntegerField(
        default=0
    )


    # =========================
    # SKILLS & EXPERIENCE
    # =========================

    skills = models.TextField(
        help_text="Enter skills separated by commas"
    )

    projects = models.TextField(
        blank=True
    )

    certifications = models.TextField(
        blank=True
    )


    # =========================
    # DISPLAY NAME IN ADMIN
    # =========================

    def __str__(self):
        return self.name


class Job(models.Model):

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"

    recruiter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recruiter_jobs",
    )

    # =========================
    # COMPANY INFORMATION
    # =========================

    company_name = models.CharField(
        max_length=100
    )

    job_title = models.CharField(
        max_length=100
    )

    description = models.TextField(
        blank=True
    )


    # =========================
    # JOB REQUIREMENTS
    # =========================

    required_skills = models.TextField(
        help_text="Enter required skills separated by commas"
    )

    minimum_cgpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0
    )

    maximum_backlogs = models.IntegerField(
        default=0
    )


    # =========================
    # JOB DETAILS
    # =========================

    location = models.CharField(
        max_length=100,
        blank=True
    )

    package = models.CharField(
        max_length=100,
        blank=True
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN,
    )

    deadline = models.DateField(
        null=True,
        blank=True,
    )

    drive_date = models.DateField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )


    # =========================
    # DISPLAY NAME IN ADMIN
    # =========================

    def __str__(self):
        return f"{self.company_name} - {self.job_title}"


class Application(models.Model):
    class Status(models.TextChoices):
        APPLIED = "APPLIED", "Applied"
        SHORTLISTED = "SHORTLISTED", "Shortlisted"
        REJECTED = "REJECTED", "Rejected"
        OFFERED = "OFFERED", "Offered"

    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="applications",
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.PROTECT,
        related_name="applications",
    )

    applied_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.APPLIED,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("student", "job"),
                name="unique_application_per_student_job",
            ),
        ]