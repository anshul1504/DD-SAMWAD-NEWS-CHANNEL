# Desh Darpan Samvad

Hindi-first Django news platform with a public website, custom OTP authentication, role-based ERP shell, articles, categories, locations, advertisements, galleries, videos, web stories, live blogs, SEO metadata, sitemap and contact/newsletter storage.

## Stack

- Python 3
- Django 5.2
- SQLite for local development
- Django templates
- Bootstrap 5 and Bootstrap Icons
- Vanilla JavaScript
- Pillow for media/image handling
- python-dotenv for environment configuration

## Setup

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
python manage.py migrate
python manage.py createcachetable
python manage.py createsuperuser
python manage.py setup_portal_roles
python manage.py seed_home_demo
python manage.py seed_story_reel
python manage.py runserver
```

Open:

- Website: `http://127.0.0.1:8000/`
- Custom ERP: `http://127.0.0.1:8000/accounts/login/`
- Django Admin: `http://127.0.0.1:8000/admin/`

## Environment

Use `.env` for local secrets and runtime settings. Never commit `.env`.
Use `.env.example` for local development defaults and `.env.production.example` as the deployment checklist. Replace every production placeholder, especially `SECRET_KEY` and `EMAIL_HOST_PASSWORD`.

Important settings:

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `SITE_URL`
- `SECURE_SSL_REDIRECT`
- `SESSION_COOKIE_SECURE`
- `CSRF_COOKIE_SECURE`
- `SECURE_HSTS_SECONDS`
- `SECURE_HSTS_INCLUDE_SUBDOMAINS`
- `SECURE_HSTS_PRELOAD`
- `EMAIL_BACKEND`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_SSL`
- `EMAIL_USE_TLS`
- `DEFAULT_FROM_EMAIL`
- `SERVER_EMAIL`

For local development, `DEBUG=True` and secure cookie/SSL redirect settings can remain disabled. For production behind HTTPS, set `DEBUG=False`, use a strong secret key, configure real hosts, and enable SSL redirect, secure cookies and HSTS carefully.

Generate a new production secret key with:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Production deployment

> Full operations guide — backups, restore, monitoring, disaster scenarios, CI —
> is in [docs/deployment.md](docs/deployment.md). The summary below covers setup only.

### Cache table (required unless using Redis)

When `REDIS_URL` is not set, the cache falls back to a database table that must be
created once. OTP throttling and contact-form throttling both depend on the cache,
so this step is not optional:

```powershell
python manage.py createcachetable
```

Set `REDIS_URL` to use Redis instead (the `redis` driver is in `requirements.txt`).
A per-process `LocMemCache` is deliberately **not** used: throttle counters must be
shared across workers or the limits can be bypassed by hitting a different worker.

### Static files

WhiteNoise serves collected static files when `DEBUG=False`. Run before each deploy:

```powershell
python manage.py collectstatic --noinput
```

### Uploaded media

WhiteNoise does **not** serve `MEDIA_ROOT`. Map `MEDIA_URL` to `MEDIA_ROOT` at the
reverse proxy, or article images will 404 in production. Example nginx:

```nginx
location /media/ {
    alias /srv/dds/media/;
    expires 30d;
}
```

### Deploy sequence

```powershell
pip install -r requirements.txt
python manage.py migrate
python manage.py createcachetable        # skip only if REDIS_URL is set
python manage.py collectstatic --noinput
python manage.py check --deploy          # run with the production .env
```

## OTP Email

The ERP authentication flow uses email OTP for:

- Login
- Signup verification
- Forgot password
- Password reset authorization

For local tests, use Django's in-memory or console email backend. For real delivery, configure SMTP values in `.env`. `.env.example` must contain placeholders only.

The previously exposed SMTP mailbox password should be rotated before deployment. Put the rotated password only in the real `.env` or hosting secret manager, never in Git-tracked files.

## Roles

Run:

```powershell
python manage.py setup_portal_roles
```

Created role groups:

- Guest
- Admin
- Editor
- Reporter
- SEO Manager
- Ads Manager
- Media Manager
- Live Desk

New signup users are activated after OTP verification and assigned the Guest role. An admin can later assign newsroom roles.

## Public Routes

- `/`
- `/latest/`
- `/trending/`
- `/search/`
- `/category/<slug>/`
- `/tag/<slug>/`
- `/state/<slug>/`
- `/state/<state>/<district>/`
- `/state/<state>/<district>/<city>/`
- `/news/<slug>/`
- `/photos/`
- `/photos/<slug>/`
- `/videos/`
- `/videos/<slug>/`
- `/web-stories/`
- `/web-stories/<slug>/`
- `/live/`
- `/live/<slug>/`
- `/sitemap.xml`
- `/robots.txt`

## ERP Routes

- `/accounts/login/`
- `/accounts/signup/`
- `/accounts/verify-otp/`
- `/accounts/forgot-password/`
- `/accounts/reset-password/`
- `/accounts/dashboard/`
- `/accounts/portal/<module>/`

The ERP shell currently provides dashboard, authentication, role-aware navigation, module listing and access control foundations. Full custom CRUD screens for all content modules are planned for the next phase and should not be treated as complete yet.

## Development Commands

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --plan
python manage.py test
```

## Demo Data

```powershell
python manage.py seed_home_demo
python manage.py seed_story_reel
```

These commands seed local demo content and images for homepage and story UI testing. Do not rely on demo data for production.

## Production Notes

- Use PostgreSQL for production.
- Serve static files through Nginx/CDN.
- Serve media uploads from persistent storage or object storage.
- Run `python manage.py collectstatic --noinput` during deployment.
- Enable HTTPS and secure cookie settings.
- Rotate any credential that was ever exposed outside `.env`.
- Add monitoring, backups and error logging before launch.

## Git Workflow

Recommended:

- `main` for stable code
- `dev` for active development
- feature branches for ERP modules, UI passes and security work

Do not commit:

- `.env`
- `db.sqlite3`
- `media/`
- `staticfiles/`
- logs or local virtual environments
