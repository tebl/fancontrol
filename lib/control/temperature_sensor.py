from ..exceptions import *
from .sensor import Sensor


class TemperatureSensor(Sensor):
    def __init__(self, controller, settings, logger, name, device_path, auto_load=True):
        super().__init__(controller, settings, logger, name, device_path, auto_load=auto_load)


    def format_value(self, value):
        return str(value) + "°C"


    def read_int(self, sensor_path):
        return super().read_int(sensor_path) / 1000.0