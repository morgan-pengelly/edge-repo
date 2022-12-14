#!/bin/bash
PATH="/usr/sbin:/usr/bin:/sbin:/bin"
MYDIR="$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"
APPDIR="${MYDIR%/*}"
LOGDIR="$APPDIR/logs"
LOGFILE="$LOGDIR/edge-camsys.log"
fuser -k "$LOGFILE"
sleep 1
echo "Staring keep_logs at $(date)" >> "$LOGFILE"
nohup docker logs --follow edge-camsys >> "$LOGFILE"  2>&1  &
