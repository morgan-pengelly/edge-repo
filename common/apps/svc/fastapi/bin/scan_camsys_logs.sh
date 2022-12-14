#!/bin/bash

#=========================== Customizable section =============================
NLINES="50"
INTERVAL="15"
ERRORLOG="/home/edge/apps/camsys/logs/inference_engine.log"
EVENTLOG="/home/edge/apps/camsys/logs/edge-camsys.log"
#=======================i End of customizable section =========================

PATH="/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
MYDIR="$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"
APPDIR="${MYDIR%/*}"
BASEDIR="${APPDIR%/*}"
APPNAME="${APPDIR##*/}"
DOCKER_NAME="edge-$APPNAME"
PRGNAME="${0##*/}"

Abort()
{
  echo "$(date '+%F %T') - $PRGNAME: $*"1>&2
  exit 1
}

InitLog() {
  local LOG="$1"
  touch --date="1970-01-01 00:00:00" "$LOG"
  chmod 644 "$LOG"
}

test -d "$APPDIR/data" || install -d o root -g root -m 755 "$APPDIR/data"

ERRORJS="$APPDIR/data/errorlog.js"
EVENTJS="$APPDIR/data/eventlog.js"

[ -r "$ERRORJS" ] || InitLog "$ERRORJS"
[ -r "$EVENTJS" ] || InitLog "$EVENTJS"

#ERRORPAT="INFO no response from|INFO cam.* with rtsp://|INFO cam.* is now connected|INFO Got EOS from stream"
ERRORPAT="INFO cam.* is not responding|INFO cam.* with rtsp://|INFO cam.* is now connected|INFO Got EOS from stream"
EVENTPAT="Status change for cam"

while :
do
  if [ -f "$ERRORLOG" ] && [ "$ERRORLOG" -nt "$ERRORJS" ]
  then
    {
      echo -n "["
      egrep "$ERRORPAT" "$ERRORLOG" | tail -$NLINES | tac | \
        sed -n 's!^.*- \([^ ]* [^ ]*\) INFO \(.*\)$!{"date":"\1","message":"\2"},!p' | \
          tr -d '\n' | sed 's/,$//'
      echo "]"
    } > "$ERRORJS"
  fi

  if [ "$EVENTLOG" -nt "$EVENTJS" ]
  then
    {
      echo -n "["
      egrep "$EVENTPAT" "$EVENTLOG" | tr -d '\r' | tail -$NLINES | tac | \
        sed -n 's!^\([^ ]* [^ ]*\) \(.*\)$!{"date":"\1","message":"\2"},!p' | \
	  tr -d '\n' | sed 's/,$//'
      echo "]"
    } > "$EVENTJS"
  fi
  sleep $INTERVAL
done
