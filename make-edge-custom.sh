#!/bin/bash

PRGNAME="${0##*/}"
PATH="/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
MYDIR="$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"
APPDIR="${MYDIR%/*}"

Usage()
{
  echo -e "\nUsage: $PRGNAME location1 [.. locationN]\n"
  exit 1
}

Abort()
{
  echo -e "\nERROR: $*\n"
  exit 1
}


Warning()
{
  echo -e "\nWARNING: $*\n"
}


[ $# -eq 0 ] && Usage

echo -e "\nRunning $PRGNAME $*"
cd $MYDIR/custom 2>/dev/null || Abort "cannot chdir to $MYDIR/custom."

set -o pipefail
for LOCATION in $*
do
  if ! cd $LOCATION 2>/dev/null
  then
    Warning "cannot chdir to $MYDIR/custom/$LOCATION.\nERROR: $LOCATION package was not built."
    continue
  fi
  if [ ! -d apps ]
  then
    Warning "cannot access $MYDIR/custom/$LOCATION/apps directory.\nERROR: $LOCATION package was not built."
    continue
  fi
  CUSTOMPKG="$MYDIR/packages/$LOCATION-custom.cpio.gz"
  if find apps | cpio --quiet -o | gzip -c > "$CUSTOMPKG"
  then
    echo -e "SUCCESS: $CUSTOMPKG was built correctly\n"
  else
    Warning "Error building $CUSTOMPKG"
    rm -f "$CUSTOMPKG"
  fi
done
