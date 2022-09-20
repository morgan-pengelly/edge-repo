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

Usage()
{
  echo "Usage: $PRGNAME package"
  exit 1
}

[ $# -eq 1 ] || Usage
PACKAGE="$1"
PACKAGE="${PACKAGE%.cpio.gz}.cpio.gz"
cd $MYDIR/packages 2>/dev/null || Abort "cannot chdir to $MYDIR/packages."
test -f "$PACKAGE" || Abort "cannot access $PACKAGE package."
set -o pipefail
gunzip -c "$PACKAGE" | cpio -ivt --quiet
