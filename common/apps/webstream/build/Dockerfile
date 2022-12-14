# Download base image debian latest
FROM debian:latest

# Install dependencies
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get -y install tzdata
RUN apt-get update && \
      apt-get install -y --no-install-recommends \
      build-essential \
      autoconf \
      gcc libpq-dev \
      libssl-dev \
      libcurl4-openssl-dev \
      liblog4cplus-dev \
      flex \
      bison \
      nmap \
      cmake \ 
      libglib2.0-dev \
      yasm \
      wget \
      gir1.2-gst-rtsp-server-1.0 \
      libgstreamer1.0-dev \
      libgstreamer-plugins-base1.0-dev \
      libgstreamer-plugins-bad1.0-dev \
      gstreamer1.0-plugins-base-apps \
      gstreamer1.0-plugins-base \
      gstreamer1.0-plugins-bad \
      gstreamer1.0-plugins-good \
      gstreamer1.0-plugins-ugly \
      gstreamer1.0-libav \
      gstreamer1.0-tools \
      gstreamer1.0-x \
      gstreamer1.0-alsa \
      gstreamer1.0-gl \
      gstreamer1.0-gtk3 \
      gstreamer1.0-qt5 \
      gstreamer1.0-pulseaudio \
      cmake
      
WORKDIR /home/edge

#USER ${USER_NAME}

ENTRYPOINT ["tail", "-f", "/dev/null"]
