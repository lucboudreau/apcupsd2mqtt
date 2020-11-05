
## Yet Another apcupsd2mqtt project

This is a fork of bt-mqtt-gateway from github.com/zewelor 

It was hacked to run apcupsd in a docker container and also report metrics on MQTT. The apcupsd process runs on localhost and needs access to the USB device where the APC is connected.

## Docker Compose

For docker compose, use roughly this setup. Make sure to map the USB device correctly. 

```
version: '3.7'
services:
  apcupsd2mqtt:
    image: lucboudreau/apcupsd2mqtt
    container_name: apcupsd2mqtt
    restart: unless-stopped
    volumes:
      - ./etc/apcupsd:/etc/apcupsd:rw
      - /etc/localtime:/etc/localtime:ro
    environment:
      - TZ=America/New_York
      - DEBUG=true
    network_mode: host
    devices:
      - /dev/usb/hiddev0:/dev/usb/hiddev0
    privileged: true
```

The image allows you to mount a folder at ``/etc/apcupsd`` and this folder must contain two configuration files.

### /etc/apcupsd/config.yaml

Here we configure the MQTT gateway. Update the MQTT server settings with yours. The default settings should work for Home Assistant discovery under the topic ``homeassistant``. Adjust as necessary.

```
mqtt:
  host: 192.168.1.1
  port: 1883
  username: user
  password: password
  #ca_cert: /etc/ssl/certs/ca-certificates.crt # Uncomment to enable MQTT TLS, update path to appropriate location.
  #ca_verify: False                            # Verify TLS certificate chain and host, disable for testing with self-signed certificates, default to True
  topic_prefix: home/ups
  client_id: apcupsd2mqtt
  availability_topic: LWT

manager:
  sensor_config:
    topic: homeassistant
    retain: true
  topic_subscription:
    update_all:
      topic: home/ups/apcupsd2mqtt/status
      payload: online
  command_timeout: 10           # Timeout for worker operations. Can be removed if the default of 35 seconds is sufficient.
  workers:
    apcupsd:
      args:
        devices:
          SUA750RM1U:  127.0.0.1
      update_interval: 120
```

### /etc/apcupsd/apcupsd.conf

This file will configure the local apcupsd process running in the container. Make sure that the DEVICE parameter corresponds to the one you have mapped into docker-compose under devices.

If you can't find a proper configuration file, the minimums below should get you started.

```
UPSCABLE usb
UPSTYPE usb
DEVICE /dev/usb/hiddev0
LOCKFILE /var/lock
SCRIPTDIR /etc/apcupsd
PWRFAILDIR /etc/apcupsd
NOLOGINDIR /etc
ONBATTERYDELAY 6
BATTERYLEVEL 5
MINUTES 3
TIMEOUT 0
ANNOY 300
ANNOYDELAY 60
NOLOGON disable
KILLDELAY 0
NETSERVER on
NISIP 127.0.0.1
NISPORT 3551
EVENTSFILE /var/log/apcupsd.events
EVENTSFILEMAX 10
UPSCLASS standalone
UPSMODE disable
STATTIME 0
STATFILE /var/log/apcupsd.status
LOGSTATS off
DATATIME 0
```

## License

Licensed under MIT.

Copyright (c) 2018 zewelor
Copyright (c) 2020 lucboudreau
