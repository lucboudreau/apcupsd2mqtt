FROM python:3.8-alpine3.11

ENV DEBUG false

RUN mkdir application
COPY ./application /application

WORKDIR /application
RUN chmod +x /application/start.sh && \
    apk add --no-cache apcupsd && \
    pip install -r requirements.txt

VOLUME ["/etc/apcupsd"]

ENTRYPOINT ["/bin/sh", "-c", "/application/start.sh"]
