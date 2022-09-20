docker stop edge-api 2>/dev/null
docker build --build-arg USER_ID=$(id -u edge) -t edge-api .
##docker image prune
