# using ubuntu LTS version
FROM ubuntu:20.04 AS builder-image

# avoid stuck build due to user prompt
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install --no-install-recommends -y python3.9 python3.9-dev python3.9-venv python3-pip python3-wheel build-essential && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# create and activate virtual environment
# using final folder name to avoid path issues with packages
RUN python3.9 -m venv /home/myuser/venv
ENV PATH="/home/myuser/venv/bin:$PATH"

# install requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir wheel
RUN pip3 install --no-cache-dir -r requirements.txt

FROM ubuntu:20.04 AS runner-image
RUN apt-get update && apt-get install --no-install-recommends -y python3.9 python3-venv && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

#install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

RUN useradd --create-home myuser
COPY --from=builder-image /home/myuser/venv /home/myuser/venv

USER myuser
RUN mkdir /home/myuser/app
WORKDIR /home/myuser/app

# make sure all messages always reach console
ENV PYTHONUNBUFFERED=1

# activate virtual environment
ENV VIRTUAL_ENV=/home/myuser/venv
ENV PATH="/home/myuser/venv/bin:$PATH"

# Or any preferred Python version.
# COPY ./core core
# COPY ./app_main.py .
# COPY ./custom custom
#./logs is mounted during run command
#./data  is mounted during run command

EXPOSE 8000:8000
# FROM : https://docs.docker.com/engine/reference/builder/
#The EXPOSE instruction does not actually publish the port.
#It functions as a type of documentation between the person who builds the image
# and the person who runs the container, about which ports are intended 
#to be published. To actually publish the port when running the container, 
#use the -p flag on docker run to publish and map one or more ports, or the -P 
#flag to publish all exposed ports and map them to high-order ports.

#
CMD [ "python", "app_main.py" ]