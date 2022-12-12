cd ../../
DOCKER_NAME="ml-client"
#Remove existing contaier if it exists.
docker ps -qa --filter "name=$DOCKER_NAME" | grep -q . && echo "Container already exists, stopping and removing..."
docker ps -qa --filter "name=$DOCKER_NAME" | grep -q . && docker stop $DOCKER_NAME > /dev/null && docker rm -fv $DOCKER_NAME > /dev/null
#Build container and tage anti-collison and latest.
echo "Building Container..."
docker build -qt ml_client:anti_collision -t ml_client:latest . 
cd core/bin
bash run.sh
# docker run \
# 	--net mynet123 \
# 	--ip 172.69.0.22 \
# 	-i \
# 	-p 8000:8000 \
# 	-v $PWD/custom:/home/myuser/app/custom \
# 	-v $PWD/logs:/home/myuser/app/logs \
# 	-v $PWD/data:/home/myuser/app/data \
# 	-v $PWD/ftp:/home/myuser/app/ftp \
# 	-v $PWD/video:/home/myuser/app/video \
# 	ml_client:anti_collision
