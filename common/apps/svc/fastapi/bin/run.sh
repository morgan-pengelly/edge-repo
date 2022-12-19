#!/bin/bash

PATH="/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
MYDIR="$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"
APPDIR="${MYDIR%/*}"
BASEDIR="${APPDIR%/*}"
CONFIGDIR="$APPDIR/config"
DATADIR="$APPDIR/data"

MODE="${1:--i}"
case "$MODE" in
-d) docker stop edge-api 2>/dev/null ;;
esac

SCAN_CAMSYS_LOGS="$APPDIR/bin/scan_camsys_logs.sh"
pkill -f "$SCAN_CAMSYS_LOGS" >/dev/null 2>&1
nohup "$SCAN_CAMSYS_LOGS" </dev/null >/dev/null 2>&1 &

docker run \
	-p 8000:8000 \
	-t $MODE \
	--name edge-api \
	--link edge-redis \
	--net="host" \
	--hostname edge-api \
	--add-host jetson:172.17.0.1 \
	-v $CONFIGDIR:/app/app \
	-v $DATADIR:/app/data \
	--rm \
	edge-api
