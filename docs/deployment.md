# AWS Deployment Guide

This guide targets a simple production setup on one EC2 instance with Nginx,
Gunicorn, WhiteNoise for static files, and either RDS PostgreSQL or local
SQLite. RDS PostgreSQL is recommended for real traffic.

## 1. AWS Resources

- EC2: Ubuntu 24.04 LTS, at least t3.small for production.
- Security group: allow inbound 22 from your IP, 80 and 443 from the internet.
- Elastic IP: attach one stable public IP to the instance.
- Domain DNS: point `ddsamvad.com` and `www.ddsamvad.com` to the Elastic IP.
- Optional but recommended: RDS PostgreSQL in the same region/VPC.
- Optional: ElastiCache Redis for shared throttling/cache.

## 2. Server Packages

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip git nginx certbot python3-certbot-nginx
```

## 3. App User And Code

```bash
sudo adduser --system --group --home /srv/ddsamvad ddsamvad
sudo mkdir -p /srv/ddsamvad/app /srv/ddsamvad/media /srv/ddsamvad/logs
sudo chown -R ddsamvad:ddsamvad /srv/ddsamvad
sudo -u ddsamvad git clone <YOUR_REPO_URL> /srv/ddsamvad/app
cd /srv/ddsamvad/app
sudo -u ddsamvad python3 -m venv .venv
sudo -u ddsamvad .venv/bin/pip install --upgrade pip
sudo -u ddsamvad .venv/bin/pip install -r requirements.txt
```

## 4. Production Environment

Create `/srv/ddsamvad/app/.env`:

```bash
SECRET_KEY=<generate-a-real-django-secret-key>
DEBUG=False
ALLOWED_HOSTS=ddsamvad.com,www.ddsamvad.com,<EC2_PUBLIC_IP>
SITE_URL=https://ddsamvad.com
CSRF_TRUSTED_ORIGINS=https://ddsamvad.com,https://www.ddsamvad.com

SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=False
SECURE_PROXY_SSL_HEADER_NAME=HTTP_X_FORWARDED_PROTO
SECURE_PROXY_SSL_HEADER_VALUE=https

MEDIA_ROOT=/srv/ddsamvad/media

# RDS PostgreSQL, recommended:
DATABASE_URL=postgres://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require
DATABASE_CONN_MAX_AGE=600

# Optional Redis:
REDIS_URL=

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=sys19.prosuperservers.com
EMAIL_PORT=465
EMAIL_HOST_USER=info@ddsamvad.com
EMAIL_HOST_PASSWORD=<rotated-real-password>
EMAIL_USE_SSL=True
EMAIL_USE_TLS=False
DEFAULT_FROM_EMAIL=info@ddsamvad.com
SERVER_EMAIL=info@ddsamvad.com
EMAIL_TIMEOUT=20
```

Generate the key locally or on the server:

```bash
/srv/ddsamvad/app/.venv/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 5. Database And Static Files

```bash
cd /srv/ddsamvad/app
sudo -u ddsamvad .venv/bin/python manage.py migrate
sudo -u ddsamvad .venv/bin/python manage.py createcachetable
sudo -u ddsamvad .venv/bin/python manage.py collectstatic --noinput
sudo -u ddsamvad .venv/bin/python manage.py check --deploy
```

Skip `createcachetable` only when `REDIS_URL` is set.

## 6. Gunicorn Systemd Service

Create `/etc/systemd/system/ddsamvad.service`:

```ini
[Unit]
Description=Desh Darpan Samvad Django app
After=network.target

[Service]
User=ddsamvad
Group=www-data
WorkingDirectory=/srv/ddsamvad/app
EnvironmentFile=/srv/ddsamvad/app/.env
ExecStart=/srv/ddsamvad/app/.venv/bin/gunicorn config.wsgi:application --bind unix:/run/ddsamvad/gunicorn.sock --workers 3 --timeout 60
RuntimeDirectory=ddsamvad
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ddsamvad
sudo systemctl status ddsamvad
```

## 7. Nginx

Create `/etc/nginx/sites-available/ddsamvad`:

```nginx
server {
    listen 80;
    server_name ddsamvad.com www.ddsamvad.com;

    client_max_body_size 10M;

    location /media/ {
        alias /srv/ddsamvad/media/;
        expires 30d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://unix:/run/ddsamvad/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable it:

```bash
sudo ln -s /etc/nginx/sites-available/ddsamvad /etc/nginx/sites-enabled/ddsamvad
sudo nginx -t
sudo systemctl reload nginx
```

## 8. HTTPS

```bash
sudo certbot --nginx -d ddsamvad.com -d www.ddsamvad.com
sudo systemctl reload nginx
```

After HTTPS works, keep the secure settings in `.env` enabled.

## 9. Deploy Updates

```bash
cd /srv/ddsamvad/app
sudo -u ddsamvad git pull
sudo -u ddsamvad .venv/bin/pip install -r requirements.txt
sudo -u ddsamvad .venv/bin/python manage.py migrate
sudo -u ddsamvad .venv/bin/python manage.py createcachetable
sudo -u ddsamvad .venv/bin/python manage.py collectstatic --noinput
sudo -u ddsamvad .venv/bin/python manage.py check --deploy
sudo systemctl restart ddsamvad
sudo systemctl reload nginx
```

## 10. Health, Logs, And Backups

Health endpoint:

```bash
curl -I https://ddsamvad.com/healthz
```

Logs:

```bash
sudo journalctl -u ddsamvad -n 100 --no-pager
sudo tail -n 100 /var/log/nginx/error.log
```

Backups for SQLite/media:

```bash
APP_DIR=/srv/ddsamvad/app MEDIA_DIR=/srv/ddsamvad/media BACKUP_DIR=/srv/ddsamvad/backups /srv/ddsamvad/app/scripts/backup.sh
```

For RDS, enable automated backups and snapshots in AWS. Keep media backups or
move uploads to S3 in a later phase.
