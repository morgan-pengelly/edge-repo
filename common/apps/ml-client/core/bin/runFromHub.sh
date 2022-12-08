cd ../../
docker login -u nnfuller -p L###B######
docker run \
	--net mynet123 \
	--ip 172.69.0.22 \
	-i \
	-p 8000:8000 \
	-v $PWD/custom:/home/myuser/app/custom \
	-v $PWD/logs:/home/myuser/app/logs \
	-v $PWD/data:/home/myuser/app/data \
	-v $PWD/ftp:/home/myuser/app/ftp \
	-v $PWD/video:/home/myuser/app/video \
	nnfuller/ml_client:anti_collision