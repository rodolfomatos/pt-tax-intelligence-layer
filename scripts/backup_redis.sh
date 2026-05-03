#!/bin/bash
# Redis Backup Script
# Usage: ./scripts/backup_redis.sh [output_dir]

set -e

BACKUP_DIR="${1:-/backups/redis}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/redis_dump_${TIMESTAMP}.rdb"

echo "Starting Redis backup..."
mkdir -p "${BACKUP_DIR}"

# Get Redis URL
REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
# Parse host and port
REDIS_HOST=$(echo $REDIS_URL | sed -n 's|redis://\([^:]*\).*|\1|p')
REDIS_PORT=$(echo $REDIS_URL | sed -n 's|redis://[^:]*:\([0-9]*\).*|\1|p')
REDIS_DB=$(echo $REDIS_URL | sed -n 's|.*/\([0-9]*$\)|\1|p')

# Trigger SAVE command
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" SAVE

# Copy dump.rdb from Redis config dir
REDIS_CONF=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" CONFIG GET dir | tail -1)
if [ -z "$REDIS_CONF" ]; then
    REDIS_CONF="/data"
fi
RDB_SOURCE="${REDIS_CONF}/dump.rdb"

if [ ! -f "$RDB_SOURCE" ]; then
    echo "ERROR: dump.rdb not found at $RDB_SOURCE"
    exit 1
fi

cp "$RDB_SOURCE" "$BACKUP_FILE"

# Keep only last 7 backups
ls -t "${BACKUP_DIR}/redis_dump_"*.rdb | tail -n +8 | xargs -r rm --

echo "Redis backup completed: $BACKUP_FILE"
echo "Size: $(du -h $BACKUP_FILE | cut -f1)"
