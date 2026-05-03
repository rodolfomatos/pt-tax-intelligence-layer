#!/bin/bash
# Setup backup cron jobs
# Run this script as root or with appropriate permissions

set -e

CRON_USER="${1:-root}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# PostgreSQL backup daily at 2 AM
(crontab -l -u "$CRON_USER" 2>/dev/null | grep -v "/backups/postgres/backup_postgres.sh" || true) ; (crontab -l -u "$CRON_USER" 2>/dev/null ; echo "0 2 * * * ${SCRIPT_DIR}/backup_postgres.sh /backups/postgres >> /var/log/postgres_backup.log 2>&1") | crontab -u "$CRON_USER" -

# Redis backup hourly at minute 15
(crontab -l -u "$CRON_USER" 2>/dev/null | grep -v "/backups/redis/backup_redis.sh" || true) ; (crontab -l -u "$CRON_USER" 2>/dev/null ; echo "15 * * * * ${SCRIPT_DIR}/backup_redis.sh /backups/redis >> /var/log/redis_backup.log 2>&1") | crontab -u "$CRON_USER" -

echo "Backup cron jobs installed for user: $CRON_USER"
echo "PostgreSQL daily at 2 AM"
echo "Redis hourly at minute 15"
