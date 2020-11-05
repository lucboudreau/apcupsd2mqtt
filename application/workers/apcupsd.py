from exceptions import DeviceTimeoutError
from mqtt import MqttMessage, MqttConfigMessage
from apcaccess import status as apc
from interruptingcow import timeout
from workers.base import BaseWorker
import logger
import json
import time
from contextlib import contextmanager

monitoredAttrs = ["STATUS","BCHARGE","TIMELEFT","LOADPCT","LINEV","ITEMP","BATTV","OUTPUTV","NOMOUTV","NOMBATTV","LOTRANS","HITRANS"]

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
            
            if self.availability_topic is not None:
                payload.update({"avty_t": self.availability_topic})

            if attr == "STATUS":
                payload.update({"icon":"mdi:information"})
            elif attr == "BCHARGE":
                payload.update({"icon":"mdi:battery-charging","unit_of_measurement":"%"})
            elif attr == "TIMELEFT":
                payload.update({"icon":"mdi:timer-sand","unit_of_measurement":"minutes"})
            elif attr == "LOADPCT":
                payload.update({"icon":"mdi:battery-charging","unit_of_measurement":"%"})
            elif attr == "LINEV":
                payload.update({"icon":"mdi:current-ac","unit_of_measurement":"V"})
            elif attr == "BATTV":
                payload.update({"icon":"mdi:current-dc","unit_of_measurement":"V"})
            elif attr == "ITEMP":
                payload.update({"icon":"mdi:thermometer","unit_of_measurement":"°C"})
            elif attr == "OUTPUTV":
                payload.update({"icon":"mdi:current-ac","unit_of_measurement":"V"})
            elif attr == "NOMOUTV":
                payload.update({"icon":"mdi:current-ac","unit_of_measurement":"V"})
            elif attr == "NOMBATTV":
                payload.update({"icon":"mdi:current-dc","unit_of_measurement":"V"})
            elif attr == "LOTRANS":
                payload.update({"icon":"mdi:current-ac","unit_of_measurement":"V"})
            elif attr == "HITRANS":
                payload.update({"icon":"mdi:current-ac","unit_of_measurement":"V"})

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
            elif attr == "LOADPCT":
                attrValue = poller.getLoadPct()
            elif attr == "LINEV":
                attrValue = poller.getLineV()
            elif attr == "BATTV":
                attrValue = poller.getBattV()
            elif attr == "ITEMP":
                attrValue = poller.getITemp()
            elif attr == "OUTPUTV":
                attrValue = poller.getOutputV()
            elif attr == "NOMOUTV":
                attrValue = poller.getNomOutV()
            elif attr == "NOMBATTV":
                attrValue = poller.getNomBattV()
            elif attr == "LOTRANS":
                attrValue = poller.getLoTrans()
            elif attr == "HITRANS":
                attrValue = poller.getHiTrans()

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
        self._loadpct = None
        self._linev = None
        self._battv = None
        self._itemp = None
        self._outputv = None
        self._nomoutv = None
        self._nombattv = None
        self._lotrans = None
        self._hitrans = None

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
        self._loadpct = float(ups_data.get('LOADPCT', 0.0))
        self._linev = float(ups_data.get('LINEV', 0.0))
        self._battv = float(ups_data.get('BATTV', 0.0))
        self._itemp = float(ups_data.get('ITEMP', 0.0))
        self._outputv = float(ups_data.get('OUTPUTV', 0.0))
        self._nomoutv = float(ups_data.get('NOMOUTV', 0.0))
        self._nombattv = float(ups_data.get('NOMBATTV', 0.0))
        self._lotrans = float(ups_data.get('LOTRANS', 0.0))
        self._hitrans = float(ups_data.get('HITRANS', 0.0))
        
        return self._status

    def getStatus(self):
        return self._status;

    def getBCharge(self):
        return self._bcharge;

    def getTimeLeft(self):
        return self._timeleft;
    
    def getLoadPct(self):
        return self._loadpct;
    
    def getLineV(self):
        return self._linev;
        
    def getITemp(self):
        return self._itemp;

    def getBattV(self):
        return self._battv;
    
    def getOutputV(self):
        return self._outputv;
    
    def getNomOutV(self):
        return self._nomoutv;
    
    def getNomBattV(self):
        return self._nombattv;
    
    def getLoTrans(self):
        return self._lotrans;
    
    def getHiTrans(self):
        return self._hitrans;
