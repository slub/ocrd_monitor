#!/usr/bin/env bash

export MONITOR_DB_CONNECTION_STRING=$MONITOR_DB_CONNECTION
export OCRD_BROWSER__MODE=native
export OCRD_BROWSER__WORKSPACE_DIR=/data/ocr-d
export OCRD_BROWSER__PORT_RANGE="[9000,9100]"
export OCRD_LOGVIEW__PORT=$MONITOR_PORT_LOG
export OCRD_MANAGER__URL=$MANAGER_URL

cd /usr/local/ocrd-monitor
pdm run monitor
