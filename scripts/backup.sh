#!/usr/bin/env bash
#
# Desh Darpan Samvad — database + media backup.
#
# Creates a timestamped, self-contained backup of everything that cannot be
# rebuilt from the repository: the SQLite database and uploaded media.
#
# Contains no credentials. Reads only paths, from the environment or defaults.
#
# Usage:
#   ./scripts/backup.sh                 # uses defaults below
#   BACKUP_DIR=/srv/backups ./scripts/backup.sh
#
# Schedule it with cron or a systemd timer — see docs/deployment.md. This script
# does NOT schedule itself.

# Fail loudly: exit on any error, on undefined variables, and on any failure
# inside a pipeline. Without this a failed copy would still "succeed" and
# produce a silent, empty backup — the worst possible outcome for a backup tool.
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
BACKUP_DIR="${BACKUP_DIR:-${APP_DIR}/backups}"
DB_PATH="${DB_PATH:-${APP_DIR}/db.sqlite3}"
MEDIA_DIR="${MEDIA_DIR:-${APP_DIR}/media}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
TARGET="${BACKUP_DIR}/${TIMESTAMP}"

log() { printf '[backup] %s\n' "$*"; }
fail() { printf '[backup][ERROR] %s\n' "$*" >&2; exit 1; }

[ -f "${DB_PATH}" ] || fail "Database not found at ${DB_PATH}"

mkdir -p "${TARGET}"
log "Backing up into ${TARGET}"

# --- Database -------------------------------------------------------------
# Uses SQLite's online .backup API, which takes a consistent snapshot of a live
# database while holding the right locks internally. A plain `cp` of a file
# being written can capture a torn page and produce a backup that will not open.
#
# Driven through Python rather than the sqlite3 CLI: Python is guaranteed present
# (this is a Django app), exposes the same API, and avoids the CLI's path-quoting
# differences across platforms. The snapshot is then integrity-checked, so a
# corrupt backup is caught now rather than during a restore emergency.
PYTHON_BIN="${PYTHON_BIN:-python3}"
command -v "${PYTHON_BIN}" >/dev/null 2>&1 || PYTHON_BIN=python
command -v "${PYTHON_BIN}" >/dev/null 2>&1 || fail "No python interpreter found"

DDS_DB_PATH="${DB_PATH}" DDS_TARGET="${TARGET}" "${PYTHON_BIN}" <<'PYEOF' || fail "Database snapshot failed"
import os
import sqlite3
import sys

source_path = os.environ["DDS_DB_PATH"]
target_path = os.path.join(os.environ["DDS_TARGET"], "db.sqlite3")

source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
destination = sqlite3.connect(target_path)
try:
    with destination:
        source.backup(destination)
finally:
    source.close()
    destination.close()

verify = sqlite3.connect(target_path)
try:
    result = verify.execute("PRAGMA integrity_check;").fetchone()[0]
finally:
    verify.close()

if result != "ok":
    sys.stderr.write(f"Integrity check failed: {result}\n")
    sys.exit(1)
print("[backup] Database snapshot written and integrity-checked: ok")
PYEOF

# --- Media ----------------------------------------------------------------
# .env is excluded deliberately: backups are copied around and retained far more
# widely than the application directory, and secrets belong in a secret manager.
if [ -d "${MEDIA_DIR}" ]; then
  tar --exclude='.env' \
      --exclude='*.pyc' \
      --exclude='__pycache__' \
      -czf "${TARGET}/media.tar.gz" \
      -C "$(dirname "${MEDIA_DIR}")" "$(basename "${MEDIA_DIR}")" \
    || fail "Media archive failed"
  log "Media archived ($(du -h "${TARGET}/media.tar.gz" | cut -f1))"
else
  log "WARNING: media directory ${MEDIA_DIR} not found — skipping"
fi

# --- Manifest -------------------------------------------------------------
# Records what this backup contains. Deliberately no environment dump: that
# would leak secrets into the archive.
cat > "${TARGET}/MANIFEST.txt" <<MANIFEST
Backup: ${TIMESTAMP}
Host:   $(hostname)
Source database: ${DB_PATH}
Source media:    ${MEDIA_DIR}
Contents:
  db.sqlite3     - consistent SQLite snapshot
  media.tar.gz   - uploaded media archive
Excluded: .env, secrets, staticfiles/, __pycache__
MANIFEST

# --- Retention ------------------------------------------------------------
if [ "${RETENTION_DAYS}" -gt 0 ]; then
  find "${BACKUP_DIR}" -mindepth 1 -maxdepth 1 -type d -mtime "+${RETENTION_DAYS}" \
    -exec rm -rf {} + 2>/dev/null || true
  log "Pruned backups older than ${RETENTION_DAYS} days"
fi

log "Backup complete: ${TARGET}"
