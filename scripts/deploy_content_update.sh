#!/usr/bin/env bash
set -euo pipefail

APP=/srv/ddsamvad/app
MEDIA=/srv/ddsamvad/media
RELEASE=/tmp/ddsamvad-release
ASSETS=/tmp/ddsamvad-assets
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP=/srv/ddsamvad/backups/pre-content-${STAMP}

sudo mkdir -p "$BACKUP"
sudo cp -a "$APP/db.sqlite3" "$BACKUP/db.sqlite3"
sudo tar -C "$MEDIA" -czf "$BACKUP/media.tar.gz" .
echo "Backup created: $BACKUP"

sudo cp -a "$RELEASE"/. "$APP"/
sudo chown -R ddsamvad:ddsamvad "$APP"

cd "$APP"
sudo -u ddsamvad .venv/bin/pip install -r requirements.txt
sudo -u ddsamvad .venv/bin/python manage.py migrate --noinput
sudo -u ddsamvad .venv/bin/python manage.py import_epaper \
  "$ASSETS/desh-darpan-2026-09-21.pdf" \
  --date 2026-09-21 --title "देश दर्पण संवाद - अंक 02"
sudo -u ddsamvad .venv/bin/python manage.py publish_supplied_news \
  --hanuman-image "$ASSETS/hanuman-ansh-satvik-sharma.jpg"
sudo -u ddsamvad .venv/bin/python manage.py configure_public_identity
sudo -u ddsamvad .venv/bin/python manage.py collectstatic --noinput
sudo -u ddsamvad .venv/bin/python manage.py check

sudo systemctl restart ddsamvad
sudo systemctl reload nginx
sudo systemctl --no-pager --full status ddsamvad | head -25
echo "Deployment completed; backup: $BACKUP"
