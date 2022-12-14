#!/bin/bash

docker build --build-arg USER_ID=$(id -u edge) -t arm64v8/aws-iot-greengrass  .

