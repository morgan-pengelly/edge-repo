#!/bin/bash

PATH="/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
MYDIR="$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"
APPDIR="${MYDIR%/*}"

#docker stop edge-api
#docker stop edge-redis

$APPDIR/redis/bin/run.sh -d
$APPDIR/fastapi/bin/run.sh -d
$APPDIR/nginx/bin/run.sh -d
