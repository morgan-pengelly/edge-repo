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

#docker pull amazon/aws-iot-greengrass:latest

docker run \
	--rm \
	-t $MODE \
	--name edge-gg \
	--hostname edge-gg \
	--add-host jetson:172.17.0.1 \
        --env-file $APPDIR/.env-once \
	-v $APPDIR/greengrass-v2-credentials:/root/.aws/:ro \
	-v $FIFODIR:/edge-fifo \
        -v $DEPLOYDIR:/greengrass/v2/packages/artifacts/gg-deploy-sonnys \
        -p 8883:8883 \
	arm64v8/aws-iot-greengrass:latest

