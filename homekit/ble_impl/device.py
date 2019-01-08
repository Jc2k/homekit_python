import collections
import logging
import time

import dbus

from homekit.exceptions import AccessoryNotFoundError

from . import gatt
from .manufacturer_data import parse_manufacturer_specific


logger = logging.getLogger(__name__)


class Device(gatt.Device):

    def __init__(self, *args, **kwargs):
        gatt.Device.__init__(self, *args, **kwargs, managed=False)

        self.subscribers = collections.defaultdict(list)
        self.homekit_discovery_data = self.get_homekit_discovery_data()

    @property
    def name(self):
        return self._properties.Get('org.bluez.Device1', 'Alias')

    def get_homekit_discovery_data(self):
        try:
            mfr_data = self._properties.Get('org.bluez.Device1', 'ManufacturerData')
        except dbus.exceptions.DBusException as e:
            if e.get_dbus_name() == 'org.freedesktop.DBus.Error.InvalidArgs':
                return {}
            raise

        mfr_data = dict((int(k), bytes(bytearray(v))) for (k, v) in mfr_data.items())

        if 76 not in mfr_data:
            return

        parsed = parse_manufacturer_specific(mfr_data[76])

        if parsed['type'] != 'HomeKit':
            return

        return parsed

    def connect(self):
        super().connect()

        try:
            if not self.services:
                logger.debug('waiting for services to be resolved')
                for i in range(20):
                    if self.is_services_resolved():
                        break
                    time.sleep(1)
                else:
                    raise AccessoryNotFoundError('Unable to resolve device services + characteristics')

                # This is called automatically when the mainloop is running, but we
                # want to avoid running it and blocking for an indeterminate amount of time.
                logger.debug('enumerating resolved services')
                self.services_resolved()
        except dbus.exceptions.DBusException as e:
            raise AccessoryNotFoundError('Unable to resolve device services + characteristics')

    def subscribe(self, uuid, callback):
        self.subscribers[uuid].append(callback)

    def unsubscribe(self, uuid, callback):
        self.subscribers[uuid].discard(callback)

    def properties_changed(self, sender, changed_properties, invalidated_properties):
        if 'ManufacturerData' in changed_properties:
            data = self.get_homekit_discovery_data()

            # Detect disconnected notification of state change
            # Resets back to 1 after overflow, factory reset or firmware update
            if data['gsn'] != self.homekit_discovery_data.get('gsn', None):
                for sub in self.subscribers['gsn']:
                    sub('gsn')

            # Detect notification of config change - increments after firmware update
            # Device may have different characteristics
            if data['cn'] != self.homekit_discovery_data.get('cn', None):
                for sub in self.subscribers['cn']:
                    sub('cn')

        return gatt.Device.properties_changed(self, sender, changed_properties, invalidated_properties)

    def disconnect_succeeded(self):
        for sub in self.subscribers['disconnect']:
            sub('disconnect')

    def characteristic_value_updated(self, characteristic, value):
        if value != b'':
            # We are only interested in in blank values
            return

        for subscriber in self.subscribers[characteristic.uuid]:
            subscriber(characteristic.uuid)

    def characteristic_read_value_failed(self, characteristic, error):
        logger.debug('read failed: %s %s', characteristic, error)
        #self.disconnect()

    def characteristic_write_value_succeeded(self, characteristic):
        logger.debug('write success: %s', characteristic)

    def characteristic_write_value_failed(self, characteristic, error):
        logger.debug('write failed: %s %s', characteristic, error)


class DeviceManager(gatt.DeviceManager):

    discover_callback = None
    Device = Device

    def make_device(self, mac_address):
        return self.Device(mac_address=mac_address, manager=self)
