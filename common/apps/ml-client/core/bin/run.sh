# Get Directory of Bash Script
MYDIR="$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"
APPDIR="${MYDIR%/*}"
BASEDIR="${APPDIR%/*}"
COREDIR="$BASEDIR/core"
CUSTOMDIR="$BASEDIR/custom"
APP="$BASEDIR/app_main.py"
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

cd ../../
docker run \
	--name $DOCKER_NAME \
  --hostname $DOCKER_NAME \
	--ip 172.69.0.22 \
	-i \
  -v $COREDIR:/home/myuser/app/core \
  -v $CUSTOMDIR:/home/myuser/app/custom \
  -v $APP:/home/myuser/app/app_main.py \
	-v $CONFDIR:/home/myuser/app/config \
	-v $DATADIR:/home/myuser/app/data \
	-p 5605:8000 \
	ml_client:anti_collision


#-v $PWD/logs:/home/myuser/app/logs \
#-v $PWD/video:/home/myuser/app/video \
#-v $PWD/logs:/home/myuser/app/logs \