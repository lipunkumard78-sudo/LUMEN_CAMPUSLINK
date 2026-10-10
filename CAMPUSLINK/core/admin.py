from django.contrib import admin
from .models import Student, Job


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "branch",
        "cgpa",
        "backlogs",
        "technical_score",
        "aptitude_score",
        "communication_score",
        "interview_score",
    )


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):

    list_display = (
        "company_name",
        "job_title",
        "minimum_cgpa",
        "maximum_backlogs",
        "location",
        "package",
    )