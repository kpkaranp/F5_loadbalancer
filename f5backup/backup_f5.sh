#!/bin/bash

set -e

F5_HOST="$1"
F5_USER="$2"
F5_PASS="$3"
BACKUP_NAME="auto_backup_$(date +%Y%m%d_%H%M%S).ucs"

echo "Creating backup: $BACKUP_NAME"

# Trigger UCS backup
curl -sku "$F5_USER:$F5_PASS" -X POST \
  "https://${F5_HOST}/mgmt/tm/sys/ucs" \
  -H "Content-Type: application/json" \
  -d "{\"command\":\"save\",\"name\":\"$BACKUP_NAME\"}"

# Download UCS backup to artifacts directory
curl -sku "$F5_USER:$F5_PASS" \
  -o "./$BACKUP_NAME" \
  "https://${F5_HOST}/mgmt/shared/file-transfer/ucs-download/$BACKUP_NAME"

echo "Backup complete: $BACKUP_NAME"
