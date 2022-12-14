# Get Directory of Bash Script
MYDIR="$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"
APPDIR="${MYDIR%/*}"
BASEDIR="${APPDIR%/*}"
DATADIR="$BASEDIR/data"
CONFDIR="$BASEDIR/config"

DOCKER_NAME="ml-client"

#Ensure shared data directory exists
if [ -d "$DATADIR" ]; then
  # Take action if $DIR exists. #
  echo "Located Data Directory $DATADIR"
else
  echo "did not find $DATADIR on local device. Please check install or run setup-script install.sh"
  exit 1
fi

#Ensure shared data directory exists
if [ -d "$CONFDIR" ]; then
  # Take action if $DIR exists. #
  echo "Located Config Directory $CONFDIR"
else
  echo "did not find $CONFDIR on local device. Please check install or run setup-script install.sh"
  exit 1
fi

docker run \
	--name ml-client \
	--net mynet123  \
	--ip 172.69.0.22 \
	-i \
	-v $DATDIR:/home/myuser/app/data \
	-v $CONFDIR:/home/myuser/app/config \
	-p 5605:8000 \
	ml_client:anti_collision

