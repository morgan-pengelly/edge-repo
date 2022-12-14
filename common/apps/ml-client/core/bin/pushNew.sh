cd ../../
docker login -u nnfuller -p LegoBird3!
docker buildx create --platform linux/amd64,linux/arm64 --use
docker buildx build --push \
--platform linux/amd64,linux/arm64 \
--tag nnfuller/ml_client:anti_collision .