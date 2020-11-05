
## Yet Another apcupsd2mqtt project

This is a fork of bt-mqtt-gateway from github.com/zewelor. It was hacked to run apcupsd in a docker container and also report metrics on MQTT. The apcupsd process runs on localhost and needs access to the USB device where the APC is connected.

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
      - /var/run/dbus/system_bus_socket:/var/run/dbus/system_bus_socket
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
  topic_prefix: home/ups                       # Prefix sor sensor topics and availability_topic (not auto discovery)
  client_id: apcupsd2mqtt                      # Just a name. Put anything here.
  availability_topic: LWT                      # Used for LWT. Common to all sensors. Final topic is {topic_prefix}/availability_topic

manager:
  sensor_config:
    topic: homeassistant            # Prefix for HA auto discovery. Final topic is {topic}/{sensor name}
    retain: true                    # Normally set to true to retain sensor metadata in MQTT.
  command_timeout: 10               # Timeout for worker operations. Can be removed if the default of 35 seconds is sufficient.
  workers:
    apcupsd:                        # This maps to worker names. If you wrote your own, add.replace here.
      args:
        devices:
          SUA750RM1U:  127.0.0.1    # Use unique names here, and put IP here. Port is 3551 by default.
      update_interval: 120          # How often the values are updated in MQTT, in seconds.
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


## Auto shutdown

The docker image can be configured to trigger the graceful shutdown of the host. For this, enable ``privileged`` and share ``/var/run/dbus/system_bus_socket`` through the volume mounts.


## Metrics

Not all of the data available from apcupsd is sent to MQTT at the present. The list of supported values is [here](https://github.com/lucboudreau/apcupsd2mqtt/blob/main/workers/apcupsd.py#L11).

## License

Licensed under MIT.

Copyright (c) 2018 zewelor

Copyright (c) 2020 lucboudreau
