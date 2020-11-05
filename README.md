
## Yet Another apcupsd2mqtt project

This is a fork of bt-mqtt-gateway from github.com/zewelor. It was hacked to run apcupsd in a docker container and also report metrics on MQTT. The apcupsd process runs on localhost and needs access to the USB device where the APC UPS is connected.

* Runs apcupsd daemon in the docker container.
* Connects to MQTT.
* Adds discovery MQTT messages for Home Assistant to auto configure the sensors.
* Supports LWT messages for live status.
* Can gracefully shutdown the host when the UPS is depleted.

## Docker Compose

For docker compose, use roughly this setup. Make sure to map the USB device correctly. The privileged attribute and system_bus_socket mount are required for graceful shutdown. Use ``DEBUG=true`` for a more verbose log output in ``docker logs``.

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

The image requires you to mount a folder at path ``/etc/apcupsd`` and this folder must contain the two following configuration files.

### /etc/apcupsd/config.yaml

Here we configure the MQTT gateway. Update the MQTT server settings with yours. The default settings should work for Home Assistant discovery under the topic ``homeassistant``.

When you first start the container, if no file named ``/etc/apcupsd/config.yaml`` is found, one will be created by copying the sample from ``/application/config.yaml.example``. This default file will most likely not work. It will need to be edited. Stop the container, and make the changes needed as described below. If you are using an external mount, you may need to copy the files over first.

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

This file will configure the local apcupsd process running in the container. The full configuration manual of apcupsd is available [here](http://www.apcupsd.org/manual/).

Make sure that the DEVICE parameter corresponds to the one you have mapped into docker-compose under devices. The project ocntains a set of default files, but you may need to copy them manually depending on your final docker-compose configuration. See the folder ``etc/apcupsd`` for the sample files.


## Auto shutdown

The docker image can be configured to trigger the graceful shutdown of the host. For this, enable ``privileged`` and share ``/var/run/dbus/system_bus_socket`` through the volume mounts.


## Metrics

Not all of the data available from apcupsd is sent to MQTT at the present. The list of supported values is [here](https://github.com/lucboudreau/apcupsd2mqtt/blob/main/workers/apcupsd.py#L11).

## License

Licensed under MIT.

Copyright (c) 2018 zewelor

Copyright (c) 2020 lucboudreau
