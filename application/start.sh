#!/bin/sh

if ! [ -f '/etc/apcupsd/config.yaml' ]; then
    echo "There is no config.yaml! An example is created."
	cp /application/config.yaml.example /etc/apcupsd/config.yaml
    exit 1
fi

/sbin/apcupsd --version
/sbin/apcupsd
sleep 5

cd /application
if [ "$DEBUG" = 'true' ]; then
    echo "Start in debug mode"
    python3 ./gateway.py -d
    status=$?
    echo "Gateway died..."
    exit $status
else
    echo "Start in normal mode"
    python3 ./gateway.py
fi
