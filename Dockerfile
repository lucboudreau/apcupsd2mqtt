FROM alpine:latest

ENV DEBUG false

RUN mkdir application
COPY ./application /application

RUN apk update && \
    apk --no-cache -U upgrade && \
    apk add --no-cache \
    python3 py3-virtualenv py3-pip apcupsd \
    && rm -rf ~/.cache/* /usr/local/share/man /tmp/*

WORKDIR /application

RUN chmod +x /application/start.sh \
    && python3 -m venv .venv \
    && /application/.venv/bin/python -m pip install --upgrade pip \
    && /application/.venv/bin/python -m pip install -r requirements.txt

VOLUME ["/etc/apcupsd"]

ENTRYPOINT ["/bin/sh", "-c", "/application/start.sh"]
