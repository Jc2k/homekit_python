from .device import DeviceManager


class DiscoveryDeviceManager(DeviceManager):

    discover_callback = None

    def make_device(self, mac_address):
        device = super().make_device(mac_address=mac_address)
        if not device.homekit_discovery_data:
            return
        self._manage_device(device)
        if self.discover_callback:
            self.discover_callback(device)

    def start_discovery(self, callback=None):
        self.discover_callback = callback
        return super().start_discovery()
