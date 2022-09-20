#!/bin/bash 

PATH="/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
MYDIR="$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"
APPDIR="${MYDIR%/*}"
BASEDIR="${APPDIR%/*}"
LIBDIR="$APPDIR/lib"
CONFDIR="$APPDIR/config"
DOCKER_NAME="edge-webstream"
APPLOG="$APPDIR/log/$DOCKER_NAME.log"

#pkill -f "docker-watchdog $DOCKER_NAME"

if ! docker ps --format '{{.Names}}' --filter "name=edge-camsys" | grep -q "^edge-camsys"
then
  echo "WARNING: edge-camsys docker is not running. Please start it and try again." | tee -a "$APPLOG"
  exit 1
fi

while ! netstat -ltn | grep -q 554
do
  echo "Waiting for RTSP service ..." | tee -a "$APPLOG"
  sleep 5
done

pkill -f "webstream-watchdog"

MODE="${1:--i}"
case "$MODE" in
-d) docker stop $DOCKER_NAME 2>/dev/null
    docker rm $DOCKER_NAME 2>/dev/null
    sleep 5
    ;;
esac

docker run \
	-t $MODE \
	--name $DOCKER_NAME \
	--hostname $DOCKER_NAME \
	--add-host jetson:172.17.0.1 \
	-v $LIBDIR:/home/edge/lib \
	-p 8080:8080 \
	--rm \
	--entrypoint /home/edge/lib/run.sh \
	$DOCKER_NAME

case "$MODE" in
-d) 
  sleep 10
  nohup $APPDIR/bin/webstream-watchdog </dev/null >>$APPLOG  2>&1 &
#  nohup $BASEDIR/share/bin/docker-watchdog $DOCKER_NAME $APPDIR/bin/run.sh -d </dev/null >>$APPLOG 2>&1 &
  ;;
esac
