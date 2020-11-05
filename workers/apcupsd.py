from exceptions import DeviceTimeoutError
from mqtt import MqttMessage, MqttConfigMessage
from apcaccess import status as apc
from interruptingcow import timeout
from workers.base import BaseWorker
import logger
import json
import time
from contextlib import contextmanager

monitoredAttrs = ["STATUS","BCHARGE","TIMELEFT"]

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
            "name": self.format_discovery_name(name),
        }

        for attr in monitoredAttrs:
            payload = {
                "unique_id": self.format_discovery_id(ip, name, attr),
                "state_topic": self.format_prefixed_topic(name, attr),
                "name": self.format_discovery_name(name, attr),
                "device": device,
                "force_update": "true",
                "expire_after": 0,
            }

            if attr == "STATUS":
                payload.update({"icon":"mdi:information"})
            elif attr == "BCHARGE":
                payload.update({"icon":"mdi:battery-unknown","device_class":"power","unit_of_measurement":"%"})
            elif attr == "TIMELEFT":
                payload.update({"icon":"mdi:timer-sand","unit_of_measurement":"minutes"})

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

            if attr == "STATUS":
                attrValue = poller.getStatus()
            elif attr == "BCHARGE":
                attrValue = poller.getBCharge()
            elif attr == "TIMELEFT":
                attrValue = poller.getTimeLeft()

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

        self._status = None
        self._bcharge = None
        self._timeleft = None

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
            status = self.getStatus()

            return {
                "STATUS": status
            }

    def getData(self, device):
        ups_data = apc.parse(device, strip_units=True)
        _LOGGER.debug("ups data: %s", ups_data)
        
        self._status = ups_data.get('STATUS', 'Unknown')
        self._bcharge = float(ups_data.get('BCHARGE', 0.0))
        self._timeleft = float(ups_data.get('TIMELEFT', 0.0))
        return self._status

    def getStatus(self):
        return self._status;

    def getBCharge(self):
        return self._bcharge;

    def getTimeLeft(self):
        return self._timeleft;
