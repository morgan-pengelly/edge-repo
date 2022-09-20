#!/bin/bash

PRGNAME="${0##*/}"
PATH="/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
MYDIR="$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"
APPDIR="${MYDIR%/*}"
EDGEDIR="/home/edge"

Abort()
{
  echo -e "\nERROR: $*\n"
  exit 1
}

Usage()
{
  echo "Usage: $PRGNAME package"
  exit 1
}

[ $# -eq 1 ] || Usage
LOCATION="$1"
cd $MYDIR 2>/dev/null || Abort "cannot chdir to $MYDIR."
test -d "custom/$LOCATION" || Abort "cannot access custom/$LOCATION."
set -o pipefail
trap "rm -f /tmp/$PRGNAME.$$.*" EXIT
CUSTOMTMP="/tmp/$PRGNAME.$$.customfiles"
RSYNCTMP="/tmp/$PRGNAME.$$.syncommon"
(cd custom/$LOCATION && find apps | sort > $CUSTOMTMP)
rsync -n -avc "$EDGEDIR/apps" common | grep "^apps/" | grep -v "/$" | sort > $RSYNCTMP
echo -e "\n== FILES TO CHECK =="
comm -23 $RSYNCTMP $CUSTOMTMP
