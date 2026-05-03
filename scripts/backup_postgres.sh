#!/bin/bash
# PostgreSQL Backup Script
# Usage: ./scripts/backup_postgres.sh [output_dir]

set -e

BACKUP_DIR="${1:-/backups/postgres}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/tax_intelligence_${TIMESTAMP}.sql.gz"

echo "Starting PostgreSQL backup..."
mkdir -p "${BACKUP_DIR}"

# Get DB URL from env
DB_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/tax_intelligence}"
# Extract DB name
DB_NAME=$(echo $DB_URL | cut -d'/' -f4)

# Perform backup
pg_dump "$DB_URL" | gzip > "$BACKUP_FILE"

# Keep only last 7 backups
ls -t "${BACKUP_DIR}/tax_intelligence_"*.sql.gz | tail -n +8 | xargs -r rm --

echo "Backup completed: $BACKUP_FILE"
echo "Size: $(du -h $BACKUP_FILE | cut -f1)"
