from exceptions import DeviceTimeoutError
from mqtt import MqttMessage, MqttConfigMessage
from apcaccess import status as apc
from interruptingcow import timeout
from workers.base import BaseWorker
import logger
import json
import time
from contextlib import contextmanager

monitoredAttrs = ["power"]

_LOGGER = logger.get(__name__)

class ApcupsdWorker(BaseWorker):
    """
    This worker for apcupsd. It creates the sensor entries in
    MQTT for Home Assistant. It supports connection retries.
    """
    def _setup(self):
        _LOGGER.info("Adding %d %s devices", len(self.devices), repr(self))
        for name, ip in self.devices.items():
            _LOGGER.debug("Adding %s device '%s' (%s)", repr(self), name, ip)
            self.devices[name] = {
                "ip": ip,
                "poller": ApcupsdPoller(ip),
            }

    def config(self):
        ret = []
        for name, data in self.devices.items():
            ret += self.config_device(name, data["ip"])
        return ret

    def config_device(self, name, ip):
        ret = []
        device = {
            "identifiers": [ip, self.format_discovery_id(ip, name)],
            "manufacturer": "APC",
            "model": "Unknown",
            "name": self.format_discovery_name(name),
        }

        for attr in monitoredAttrs:
            payload = {
                "unique_id": self.format_discovery_id(ip, name, attr),
                "state_topic": self.format_prefixed_topic(name, attr),
                "name": self.format_discovery_name(name, attr),
                "device": device,
            }

            if attr == "power":
                payload.update({"unit_of_measurement": "W"})
                
                # payload.update({"icon": "mdi:water", "unit_of_measurement": "%"})
            #elif attr == "temperature":
            #    payload.update(
            #        {"device_class": "temperature", "unit_of_measurement": "°C"}
            #    )
            #elif attr == ATTR_BATTERY:
            #    payload.update({"device_class": "battery", "unit_of_measurement": "V"})

            ret.append(
                MqttConfigMessage(
                    MqttConfigMessage.SENSOR,
                    self.format_discovery_topic(ip, name, attr),
                    payload=payload,
                )
            )

        return ret

    def status_update(self):

        _LOGGER.info("Updating %d %s devices", len(self.devices), repr(self))

        for name, data in self.devices.items():
            _LOGGER.debug("Updating %s device '%s' (%s)", repr(self), name, data["ip"])


            try:
                with timeout(self.command_timeout, exception=DeviceTimeoutError):
                    yield self.update_device_state(name, data["poller"])
            except DeviceTimeoutError:
                logger.log_exception(
                    _LOGGER,
                    "Time out during update of %s device '%s' (%s)",
                    repr(self),
                    name,
                    data["ip"],
                    suppress=True,
                )

    def update_device_state(self, name, poller):
        ret = []
        if poller.readAll() is None :
            return ret
        for attr in monitoredAttrs:

            attrValue = None
            if attr == "power":
                attrValue = poller.getPower()
            # elif attr == "temperature":
            #     attrValue = poller.getTemperature()
            # elif attr == ATTR_BATTERY:
            #     attrValue = poller.getBattery()
            ret.append(
                MqttMessage(
                    topic=self.format_topic(name, attr),
                    payload=attrValue,
                )
            )

        return ret

class ApcupsdPoller:

    def __init__(self, ip, maxattempt=4):
        self.ip = ip
        self.maxattempt = maxattempt

        self._power = None
        #self._humidity = None
        #self._battery = None

    @contextmanager
    def connected(self):

        attempt = 1
        while attempt < (self.maxattempt + 1) :
            
            device = apc.get(host=self.ip) # def get(host="localhost", port=3551, timeout=30)
            yield device
            _LOGGER.debug("%s is disconnected ", self.ip)
            attempt = (self.maxattempt + 1) 

    def readAll(self):
        with self.connected() as device:
            if device is None :
                return None

            self.getData(device)
            power = self.getPower()

            _LOGGER.debug("successfully read %d", power)

            return {
                "power": power
                #"humidity": humidity,
                #"battery": battery,
            }

    def getData(self, device):
        ups_data = apc.parse(device, strip_units=True)
        _LOGGER.debug("ups data: %s", ups_data)
        max_watts = float(ups_data.get('NOMPOWER', 0.0))
        current_percent = float(ups_data.get('LOADPCT', 0.0))
        current_watts = ((max_watts*current_percent)/100)
        self._power = current_watts
        return self._power

    def getPower(self):
        return self._power;
