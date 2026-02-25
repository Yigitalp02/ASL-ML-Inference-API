#!/bin/bash
# Server-side setup script. Called by deploy.ps1 after file upload.
# Usage: setup-server.sh <model_filename>
set -e

MODEL_FILE="$1"

echo "  -> Moving files to /opt/stack/"
sudo mv /tmp/asl-ml-server /opt/stack/ 2>/dev/null || true
sudo chown -R bilgin:bilgin /opt/stack/asl-ml-server

echo "  -> Creating directories"
sudo mkdir -p \
    /opt/stack/config/asl-ml-api \
    /opt/stack/data/asl-ml-api/logs \
    /opt/stack/data/asl-postgres \
    /opt/stack/ai-models

echo "  -> Setting permissions"
sudo chown -R bilgin:bilgin \
    /opt/stack/config/asl-ml-api \
    /opt/stack/data/asl-ml-api \
    /opt/stack/ai-models

if [ -n "$MODEL_FILE" ] && [ -f "/tmp/$MODEL_FILE" ]; then
    echo "  -> Moving model ($MODEL_FILE) to ai-models/"
    sudo mv "/tmp/$MODEL_FILE" /opt/stack/ai-models/
    sudo chown bilgin:bilgin "/opt/stack/ai-models/$MODEL_FILE"
else
    echo "  -> No model file found in /tmp, skipping"
fi

echo "  -> Copying init script"
cp /opt/stack/asl-ml-server/init-db.sql /opt/stack/config/asl-ml-api/

echo "  -> Setup complete"
