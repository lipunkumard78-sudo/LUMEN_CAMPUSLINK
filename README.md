# CAMPUSLINK

CAMPUSLINK is a Django campus-placement workflow application for students, recruiters, and Training & Placement Officers (TPOs). It brings together student readiness, explainable job matching, applications, recruiter review, and read-only placement analytics.

## Features

- Student dashboard, job discovery and details, applications/history, and Career Twin readiness views.
- Deterministic, rule-based matching: exact case-insensitive skill comparison, CGPA and backlog eligibility, and visible match explanations. It does not use a trained AI/ML model or infer skill synonyms.
- Recruiter dashboard and job management, with job and applicant access restricted to the owning recruiter.
- TPO dashboard, student/job/application views, and analytics protected by TPO group membership.
- Django authentication, group-based authorization, CSRF-protected forms, migrations, and a repeatable fictional demo-data command.

## Technology

- Python 3.14.2 and Django 6.1.1
- SQLite for local development; PostgreSQL is supported through `DATABASE_URL`
- Django templates, WhiteNoise, Gunicorn, and Render deployment configuration

Runtime dependencies are pinned in the repository-root [`requirements.txt`](./requirements.txt). The Django/Render project also keeps a matching [`CAMPUSLINK/requirements.txt`](./CAMPUSLINK/requirements.txt) for deployments whose service root is `CAMPUSLINK/`.

## Project layout

```text
.
|-- README.md
|-- requirements.txt
|-- .gitignore
`-- CAMPUSLINK/
    |-- manage.py
    |-- render.yaml
    |-- campuslink/       Django settings and URL configuration
    `-- core/
        |-- models.py     Student, Job, and Application
        |-- views.py      Role-protected workflows and dashboards
        |-- matching.py   Deterministic matching and explanations
        |-- migrations/   Database schema history
        |-- templates/    Django templates
        `-- tests.py      Application and authorization tests
```

## Windows PowerShell setup

From the repository root:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Set-Location .\CAMPUSLINK
python manage.py migrate
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. Django's development settings default to `DEBUG=true` and SQLite when no production environment is configured. Do not use the development server or these defaults for a public production deployment.

If PowerShell blocks environment activation, use the interpreter directly from the repository root:

```powershell
.\.venv\Scripts\python.exe .\CAMPUSLINK\manage.py check
```

Run management commands from `CAMPUSLINK/`, or provide the path to its `manage.py`.

## Configuration

Local development uses SQLite (`CAMPUSLINK/db.sqlite3`) unless `DATABASE_URL` is set. This local database is ignored by Git. Production settings should be supplied through the hosting provider's environment configuration, not committed files:

| Variable | Purpose |
| --- | --- |
| `DEBUG` | Set to `false` in production. |
| `SECRET_KEY` | Required when `DEBUG=false`; provide a private, randomly generated value. |
| `ALLOWED_HOSTS` | Comma-separated allowed host names when not using Render's hostname setting. |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated trusted origins, including their URL scheme. |
| `DATABASE_URL` | Optional locally; connection URL for PostgreSQL or another supported Django database in deployment. |
| `SECURE_SSL_REDIRECT` | HTTPS redirect setting; enabled by default when `DEBUG=false`. |
| `DJANGO_EMAIL_BACKEND`, `DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_PORT`, `DJANGO_EMAIL_HOST_USER`, `DJANGO_EMAIL_HOST_PASSWORD`, `DJANGO_EMAIL_USE_TLS`, `DJANGO_EMAIL_USE_SSL` | Optional SMTP configuration. Supply credentials only through the deployment environment. |

Legacy `DJANGO_DEBUG`, `DJANGO_SECRET_KEY`, and `DJANGO_ALLOWED_HOSTS` names are also accepted. A local development-only secret fallback is used only with debug enabled; configure a real secret before production.

## Database, demo data, and accounts

Apply schema migrations with:

```powershell
python manage.py migrate
```

To add fictional presentation records to the **currently configured database**, run this optional command from `CAMPUSLINK/`:

```powershell
python manage.py seed_demo_data
```

The command is repeatable and preserves unrelated records, but it adds demo users, jobs, students, and applications. Demo accounts use a shared, published demo password; treat those credentials as public and use them only with fictional demo data. Do not seed them into a production database or use them for real people. The application does not currently implement public registration or a password-reset flow; accounts and student profile links must be provisioned administratively.

## Tests and checks

Run from `CAMPUSLINK/`:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py showmigrations
python manage.py test
```

Django's test runner creates an isolated test database; it does not require resetting the local development database.

## Deployment and limitations

See [`CAMPUSLINK/DEPLOYMENT_GUIDE.md`](./CAMPUSLINK/DEPLOYMENT_GUIDE.md) and [`CAMPUSLINK/render.yaml`](./CAMPUSLINK/render.yaml) for the existing Render setup. Configure the service's project/root directory to match the location of `manage.py`, `render.yaml`, and the nested dependency file, and set secrets through Render's environment configuration.

There is no production email provider configured by default, account registration/password reset, automated backup/monitoring setup, or historical/predictive placement model. Review the deployment guide and Django's deployment checks before exposing a deployment publicly. Generated `staticfiles/`, local databases, virtual environments, secrets, and uploaded media are excluded from Git; source templates, migrations, and application assets remain part of the project.
