#!/bin/bash

PATH="/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
MYDIR="$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"
APPDIR="${MYDIR%/*}"
BASEDIR="${APPDIR%/*}"
APPNAME="${APPDIR##*/}"
PRGNAME="${0##*/}"
CONFIG="$APPDIR/etc/${PRGNAME%%.*}.conf"
CACHE_BASE="$APPDIR/html/webcache"
API_URL="http://localhost:8000"

Abort()
{
  echo "$(date '+%F %T') - $PRGNAME: $*"1>&2
  exit 1
}

[ -r "$CONFIG" ] || Abort "cannot access $CONFIG file."

umask 0022
install -d -o root -g root -m 755 "$CACHE_BASE"
test -d "$CACHE_BASE" || Abort "cannot access $CACHE_BASE directory."

Update_Cache() {
  local API_PATH="$1"
  local API_DIR="${1%/*}"
  local API_FUNC="${1##*/}"
  local CACHE_DIR="${CACHE_BASE}${API_DIR}"
  local CACHE_FILE="$CACHE_DIR/$API_FUNC.js"

  test -d "$CACHE_DIR" || mkdir -p 755 "$CACHE_DIR"
  rm -f "$CACHE_FILE.tmp"
  if wget -q -O "$CACHE_FILE.tmp" -T 2 -t 2 "${API_URL}${API_PATH}"
  then
    [ -s "$CACHE_FILE.tmp" ] && cat "$CACHE_FILE.tmp" > "$CACHE_FILE"
  fi
  rm -f "$CACHE_FILE.tmp"
}

while :
do
  source "$CONFIG"
  [ -n "$API_REQUESTS" ] || Abort "no API_REQUESTS configuration"
  INTERVAL="${INTERVAL:-5}"
  for API_PATH in $API_REQUESTS
  do
    Update_Cache "$API_PATH"
    sleep 1
  done
  sleep $INTERVAL
done
