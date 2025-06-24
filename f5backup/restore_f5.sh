#!/bin/bash

set -e

F5_HOST="$1"
F5_USER="$2"
F5_PASS="$3"
BACKUP_FILE="$4"

echo "Uploading $BACKUP_FILE to F5..."

# Upload UCS file
curl -sku "$F5_USER:$F5_PASS" \
  --upload-file "$BACKUP_FILE" \
  "https://${F5_HOST}/mgmt/shared/file-transfer/ucs-upload/$BACKUP_FILE"

# Restore backup
curl -sku "$F5_USER:$F5_PASS" -X POST \
  "https://${F5_HOST}/mgmt/tm/sys/ucs" \
  -H "Content-Type: application/json" \
  -d "{\"command\":\"load\",\"name\":\"$BACKUP_FILE\"}"

echo "Restore initiated. Monitor F5 for reboot or reload."
