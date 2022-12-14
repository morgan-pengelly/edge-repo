FROM python:3.8-slim-buster

ARG USER_NAME=edge
ARG USER_ID=${USER_ID:-1001}
RUN useradd -m -u ${USER_ID} -s /bin/bash -c "Egde user" ${USER_NAME}
COPY ./app /app
RUN chown -R ${USER_NAME}:${USER_NAME} /app
COPY ./requirements.txt /app/requirements.txt

USER ${USER_NAME}
WORKDIR /app

ENV PATH=/home/${USER_NAME}/.local/bin:$PATH
RUN pip install --upgrade pip && \
    pip install --user --no-cache-dir --upgrade -r /app/requirements.txt

EXPOSE 8000:8000
CMD [ "uvicorn", "app.app:app", "--host", "0.0.0.0", "--reload" ]
