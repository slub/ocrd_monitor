#!/usr/bin/env bash

export MONITOR_DB_CONNECTION_STRING=$MONITOR_DB_CONNECTION
export OCRD_BROWSER__MODE=native
# all OCR-D workspaces on the Manager are under /data/ocr-d
# but since the Manager resolves everything under /data
# it tracks the workspace directory relative to that in the database
# (e.g. ocr-d/testdata-production)
# so if we write /data/ocr-d, we could list workspaces fine,
# but our workspace URLs from the job database would be wrong
# (resolving as /data/ocr-d/ocr-d/...)
# so better just use /data as well here:
export OCRD_BROWSER__WORKSPACE_DIR=/data
export OCRD_BROWSER__PORT_RANGE="[9000,9100]"
export OCRD_LOGVIEW__PORT=$MONITOR_PORT_LOG
export OCRD_MANAGER__URL=$MANAGER_URL

cd /usr/local/ocrd-monitor
pdm run monitor
