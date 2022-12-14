#!/bin/bash

PATH="/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
MYDIR="$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"
APPDIR="${MYDIR%/*}"
BASEDIR="${APPDIR%/*}"
DATADIR="$APPDIR/data"
CONFIGDIR="$APPDIR/config"

MODE="${1:--i}"

case "$MODE" in
-d) docker stop edge-redis 2>/dev/null
    docker rm edge-redis 2>/dev/null
    ;;
esac

docker run \
	-t $MODE \
	--name edge-redis \
	--hostname edge-redis \
	--ip 172.17.0.101 \
        -p 172.17.0.1:6379:6379 \
	-v $DATADIR:/data \
	-v $CONFIGDIR/redis.conf:/etc/redis.conf \
	--restart unless-stopped \
	redis redis-server /etc/redis.conf
