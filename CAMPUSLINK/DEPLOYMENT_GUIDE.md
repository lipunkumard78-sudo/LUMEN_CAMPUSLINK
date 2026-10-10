# CAMPUSLINK Render Deployment Guide

This guide deploys the existing Django app and its current database schema. The app uses Render Web Service for Django, Render Postgres for production data, WhiteNoise for Django static files, and Gunicorn as the web server. Demo records are never seeded automatically.

## 1. Files changed for deployment

- `campuslink/settings.py` reads secrets, hosts, CSRF origins, and `DATABASE_URL` from environment variables. It retains SQLite for local work and configures WhiteNoise, static collection, HTTPS handling, and secure cookies for production.
- `requirements.txt` adds PostgreSQL URL parsing, Psycopg, WhiteNoise, and Gunicorn.
- `render.yaml` describes the web service and PostgreSQL database, runs `collectstatic` during build, applies migrations before deployment, and starts Gunicorn.
- `.gitignore` excludes local secrets, the virtual environment, the local SQLite database, and generated static/media files.
- `DEPLOYMENT_GUIDE.md` provides these setup and demo instructions.

No model, migration, matching, Career Twin, authentication, or role workflow was changed. Existing migrations `0001` through `0005` are retained.

## 2. Before deploying

1. Make sure the project is in a GitHub, GitLab, or other Render-supported Git repository. The repository root should contain `render.yaml`, `manage.py`, and `requirements.txt` together.
2. Review the changes and commit/push them to your repository.
3. Do not commit `.env` files, passwords, database URLs, or the local database. `.gitignore` excludes them.

## 3. Create the Render service and database

1. Sign in at [Render](https://dashboard.render.com/).
2. Choose **New + → Blueprint**.
3. Connect the repository containing the project and select the branch you pushed.
4. Render reads `render.yaml`. Review the resources, region, and paid plans, then apply the Blueprint.
5. Render creates the `campuslink` web service and `campuslink-db` PostgreSQL database. The `DATABASE_URL` is linked internally by the Blueprint; do not copy credentials into source files.
6. The build installs `requirements.txt` and collects static files. Render runs `python manage.py migrate --noinput` before starting the service.
7. Gunicorn starts `campuslink.wsgi:application`; Django's development server is not used in production.

The included paid service/database plans avoid the short-lived, sleeping free tier. Review current Render pricing before applying the Blueprint. Both resources are placed in Singapore to keep their private connection nearby.

## 4. Environment variables

The Blueprint sets these values:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Randomly generated Django signing key. Keep it in Render's environment settings. |
| `DEBUG` | `false` in production. |
| `ALLOWED_HOSTS` | `.onrender.com`, allowing this app's Render hostname. Add an exact custom domain here if one is later configured. |
| `CSRF_TRUSTED_ORIGINS` | HTTPS Render origins accepted for CSRF-protected forms. |
| `DATABASE_URL` | Private PostgreSQL connection string supplied by Render. |
| `SECURE_SSL_REDIRECT` | Redirects HTTP requests to HTTPS. |
| `PYTHON_VERSION` | Python runtime used by the service. |

For local development, `DATABASE_URL` may be left unset to use `db.sqlite3`; set `DEBUG=true` in the local shell if your machine already defines `DEBUG=false`. The settings accept the names above; legacy `DJANGO_DEBUG`, `DJANGO_SECRET_KEY`, and `DJANGO_ALLOWED_HOSTS` are also accepted for compatibility. Never put a real production secret in a checked-in file.

## 5. Run migrations or seed demo data manually

The Render pre-deploy step runs migrations automatically for every deployment. To run them manually, open the service in Render, open **Shell**, and run:

```sh
python manage.py migrate
```

Demo data is optional and is not inserted during deploy. To seed it once on the production database, use the service Shell after the first successful deployment:

```sh
python manage.py seed_demo_data
```

The existing command is repeatable and checks for identifier collisions; it does not reset unrelated records. It creates shared demo accounts with a shared password defined in the command. Treat those credentials as public demo credentials: do not use them for real people or sensitive data, and change or remove them after the presentation. To create an administrator, use Render Shell and run `python manage.py createsuperuser`.

The command's demo accounts are `demo_student01` through `demo_student10`, `demo_recruiter01`, `demo_recruiter02`, and `demo_tpo`. Their seeded password is `CampusLinkDemo!2026` (also recorded in `core/management/commands/seed_demo_data.py`).

## 6. Find the public URL

1. In Render, open the `campuslink` Web Service.
2. On its Overview page, select the `https://...onrender.com` URL shown near the service name.
3. Open that HTTPS URL in Chrome. The home page is public; select login and use an account assigned the appropriate role.

## 7. Test from another laptop or phone

1. Copy the full `https://...onrender.com` URL from the Render service Overview.
2. On another laptop, disconnect from the development computer's network if practical, open Chrome/Firefox, and paste the URL.
3. On Android or iPhone, open Chrome or Safari and paste the same HTTPS URL. No project files, Python, Django, or VS Code are needed on the device.
4. Sign in with one of the seeded demo accounts, or with an account you created and assigned to the correct Django group/profile.
5. Check the home/login pages, student pages, recruiter pages, and TPO pages using accounts of each role. The branded 404 is available at an unknown path such as `/not-a-real-page/`.

## 8. Common deployment errors

- **Build cannot find `manage.py` or `requirements.txt`:** ensure the repository root is the `CAMPUSLINK` project directory, or configure Render's Root Directory to that folder if your Git repository contains a parent directory.
- **`DisallowedHost`:** add the service's exact hostname (without `https://`) to `ALLOWED_HOSTS` in the Render environment settings, then redeploy.
- **CSRF verification failed on login/form POST:** ensure the public HTTPS origin is present in `CSRF_TRUSTED_ORIGINS`, with scheme (for example `https://campuslink.onrender.com`), then redeploy.
- **Database connection/migration error:** verify that Render's `DATABASE_URL` is linked to `campuslink-db`, both resources are in the same region, and the database is available.
- **Static CSS/admin files missing:** check that the build log shows `collectstatic` succeeded. The generated files are served by WhiteNoise; do not commit `staticfiles/`.
- **`SECRET_KEY` or host settings error:** restore the Blueprint-generated `SECRET_KEY` and correct `ALLOWED_HOSTS`; keep `DEBUG=false`.
- **Login succeeds but a portal is forbidden or empty:** confirm the account is in the expected `STUDENT`, `RECRUITER`, or `TPO` group and student accounts have a linked Student profile. Django does not provide public sign-up in this project.
- **No email is sent:** no SMTP provider is configured. Login and portal workflows do not depend on outbound email.

## 9. Current deployment limits

- Render and the database are paid under the included plans; confirm their current price before deploying. Free Render services can sleep, and free Postgres expires, so they are not selected here.
- The project has no account registration/password-reset flow, external email service, persistent media uploads, automated backup/restore procedure, or monitoring setup. The current models do not define file uploads.
- Seeded accounts use a published shared demo password. Use them only for fictional demo data and rotate/remove them after the event.
- The public URL is created by Render after the Blueprint deploys; it cannot be known from the local project beforehand.
- `python manage.py check --deploy` may report Django's optional HSTS preload recommendation (`security.W021`). HSTS itself is enabled for production; preloading is left off because the app uses a shared Render hostname.
