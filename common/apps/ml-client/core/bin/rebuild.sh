cd ../../
docker stop ml-client
docker rm ml-client
docker network create --subnet=172.69.0.0/16 mynet123
docker build -t ml_client:anti_collision -t ml_client:latest .
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
