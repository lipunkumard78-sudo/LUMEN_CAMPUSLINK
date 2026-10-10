from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("student/", views.student_dashboard, name="student_dashboard"),
    path("student/applications/", views.student_applications, name="student_applications"),
    path("student/jobs/<int:job_id>/apply/", views.apply_to_job, name="apply_to_job"),
    path("student/career-twin/", views.career_twin, name="career_twin"),
    path("tpo/", views.tpo_dashboard, name="tpo_dashboard"),
    path("tpo/analytics/", views.tpo_analytics, name="tpo_analytics"),
    path("tpo/students/", views.tpo_students, name="tpo_students"),
    path("tpo/students/<int:student_id>/", views.tpo_student_detail, name="tpo_student_detail"),
    path("tpo/jobs/", views.tpo_jobs, name="tpo_jobs"),
    path("tpo/jobs/<int:job_id>/", views.tpo_job_detail, name="tpo_job_detail"),
    path("tpo/applications/", views.tpo_applications, name="tpo_applications"),
    path("job/<int:job_id>/", views.job_match, name="job_match"),
    path("accounts/login/", LoginView.as_view(template_name="core/login.html", next_page="home"), name="login"),
    path("accounts/logout/", LogoutView.as_view(next_page="home"), name="logout"),
    path("recruiter/", views.recruiter_dashboard, name="recruiter_dashboard"),
    path("recruiter/jobs/", views.recruiter_jobs, name="recruiter_jobs"),
    path("recruiter/jobs/create/", views.recruiter_job_create, name="recruiter_job_create"),
    path("recruiter/jobs/<int:job_id>/", views.recruiter_job_detail, name="recruiter_job_detail"),
    path("recruiter/jobs/<int:job_id>/edit/", views.recruiter_job_edit, name="recruiter_job_edit"),
    path("recruiter/jobs/<int:job_id>/status/", views.recruiter_job_toggle_status, name="recruiter_job_toggle_status"),
    path("recruiter/jobs/<int:job_id>/applications/", views.recruiter_applications, name="recruiter_applications"),
    path("recruiter/applications/<int:application_id>/status/", views.recruiter_application_status, name="recruiter_application_status"),
]
