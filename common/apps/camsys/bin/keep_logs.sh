#!/bin/bash
PATH="/usr/sbin:/usr/bin:/sbin:/bin"
LOGFILE="/home/edge/apps/camsys/logs/edge-camsys.log"
fuser -k "$LOGFILE"
sleep 1
echo "Staring keep_logs at $(date)" >> "$LOGFILE"
nohup docker logs --follow edge-camsys >> "$LOGFILE"  2>&1  &
