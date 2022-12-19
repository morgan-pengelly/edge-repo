cd ../../
DOCKER_NAME="ml-client"
#Remove existing contaier if it exists.
docker ps -qa --filter "name=$DOCKER_NAME" | grep -q . && echo "Container already exists, stopping and removing..."
docker ps -qa --filter "name=$DOCKER_NAME" | grep -q . && docker stop $DOCKER_NAME > /dev/null && docker rm -fv $DOCKER_NAME > /dev/null
#Build container and tage anti-collison and latest.
echo "Building Container..."
docker build -t $DOCKER_NAME:anti_collision -t $DOCKER_NAME:latest . 
cd core/bin
bash run.sh
