#!/bin/bash 

PATH="/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
MYDIR="$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"
APPDIR="${MYDIR%/*}"
BASEDIR="${APPDIR%/*}"
LIBDIR="$APPDIR/lib"
CONFDIR="$APPDIR/config"

DOCKER_NAME="edge-camsys"

pkill -f "docker-watchdog $DOCKER_NAME"

MODE="${1:--i}"
case "$MODE" in
-d) docker stop $DOCKER_NAME 2>/dev/null
    docker rm $DOCKER_NAME 2>/dev/null
    ;;
esac

docker run \
	-t $MODE \
        --runtime nvidia \
	--name $DOCKER_NAME \
	--hostname $DOCKER_NAME \
	--add-host jetson:172.17.0.1 \
	-v $LIBDIR:/home/edge/lib \
	-v $APPDIR/tmp:/home/edge/tmp \
	-v $APPDIR/logs:/home/edge/logs \
	-v /opt/nvidia/deepstream/deepstream-5.1:/opt/nvidia/deepstream/deepstream-5.1 \
	-p 554:554 \
	--rm \
	--entrypoint /home/edge/lib/run.sh \
	$DOCKER_NAME


case "$MODE" in
-d) nohup $BASEDIR/share/bin/docker-watchdog $DOCKER_NAME $APPDIR/bin/run.sh -d >/dev/null 2>&1 & ;;
esac

$MYDIR/keep_logs.sh
