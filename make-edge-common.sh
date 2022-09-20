#!/bin/bash

PRGNAME="${0##*/}"
PATH="/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
MYDIR="$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"
APPDIR="${MYDIR%/*}"

Abort()
{
  echo -e "\nERROR: $*\n"
  exit 1
}

echo -e "\nRunning $PRGNAME"
cd $MYDIR/common 2>/dev/null || Abort "cannot chdir to $MYDIR/common."
test -d apps || Abort "cannot access $MYDIR/common/apps directory."
COMMONPKG="$MYDIR/packages/edge-common.cpio.gz"
set -o pipefail
find apps | cpio --quiet -o | gzip -c > "$COMMONPKG"  || Abort "Error building $COMMONPKG."
echo -e "SUCCESS: $COMMONPKG was built correctly.\n"
