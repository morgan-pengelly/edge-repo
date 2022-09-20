FROM nvcr.io/nvidia/deepstream-l4t:5.1-21.02-samples

#ARG USER_NAME=edge
#ARG USER_ID=${USER_ID:-1001}
#RUN useradd -m -u ${USER_ID} -s /bin/bash -c "Egde user" ${USER_NAME}

FROM nvcr.io/nvidia/deepstream-l4t:5.1-21.02-samples

#ARG USER_NAME=edge
#ARG USER_ID=${USER_ID:-1001}
#RUN useradd -m -u ${USER_ID} -s /bin/bash -c "Egde user" ${USER_NAME}

# Install dependencies
RUN apt-get update && \
      apt-get install -y --no-install-recommends \
      build-essential \
      autoconf \
      gcc libpq-dev \
      python3-gi \
      python-gi-dev \ 
      python3-dev \
      python3-pip \
      python3-venv python3-wheel \
      python3-setuptools \
      python3-gst-1.0 \
      gir1.2-gst-rtsp-server-1.0 \
      libssl-dev \
      libcurl4-openssl-dev \
      liblog4cplus-dev \
      cmake
     
WORKDIR /home/edge/

ENV PYTHONPATH=/usr/local/lib/python3.6/dist-packages:/opt/nvidia/deepstream/deepstream-5.1/lib:/usr/lib/aarch64-linux-gnu
ENV LD_LIBRARYPATH=/usr/lib/aarch64-linux-gnu:/usr/lib/aarch64-linux-gnu/tegra


#RUN pip3 install wheel cython numpy requests
RUN pip3 install cython
RUN pip3 install numpy
RUN pip3 install requests

#USER ${USER_NAME}

ENTRYPOINT ["tail", "-f", "/dev/null"]
