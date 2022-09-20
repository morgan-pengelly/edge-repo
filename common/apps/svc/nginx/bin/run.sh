#!/bin/bash

PATH="/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
MYDIR="$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"
APPDIR="${MYDIR%/*}"
BASEDIR="${APPDIR%/*}"
DATADIR="$APPDIR/data"
CONFIGDIR="$APPDIR/config"

MODE="${1:--i}"
MAKE_CACHE="$APPDIR/bin/make_cache.sh"

case "$MODE" in
-d) 
    pkill -f "$MAKE_CACHE" >/dev/null 2>&1
    docker stop edge-nginx 2>/dev/null
    docker rm edge-nginx 2>/dev/null
    ;;
esac
 
chown -R 101.101 $DATADIR/cache $DATADIR/run

docker run \
	-t $MODE \
	--name edge-nginx \
	--hostname edge-nginx \
        -p 80:80 \
	-v $APPDIR/html:/usr/share/nginx/html \
	-v $CONFIGDIR:/etc/nginx/conf.d \
	-v $DATADIR/cache:/var/cache/nginx \
	-v $DATADIR/run:/var/run \
	--restart unless-stopped \
	nginx:latest

case "$MODE" in
-d) nohup "$MAKE_CACHE" </dev/null >/dev/null 2>&1 & ;;
esac
