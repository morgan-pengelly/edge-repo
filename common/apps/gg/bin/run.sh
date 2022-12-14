#!/bin/bash

PATH="/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
MYDIR="$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"
APPDIR="${MYDIR%/*}"
BASEDIR="${APPDIR%/*}"
FIFODIR="$BASEDIR/share/fifo"
CERTDIR="$APPDIR/certs"
CONFDIR="$APPDIR/config"
DEPLOYDIR="$APPDIR/deployment"

MODE="${1:--i}"
case "$MODE" in
-d) docker stop edge-gg 2>/dev/null ;;
esac

docker run \
	--rm \
	-t $MODE \
	--name edge-gg \
	--hostname edge-gg \
	--add-host jetson:172.17.0.1 \
        --env-file $APPDIR/.env \
	-v $FIFODIR:/edge-fifo \
	-v $CERTDIR:/tmp/certs:ro \
        -v $CONFDIR:/tmp/config/:ro \
        -v $DEPLOYDIR:/greengrass/v2/packages/artifacts/gg-deploy-sonnys \
        -p 8883:8883 \
	arm64v8/aws-iot-greengrass:latest


