from ..exceptions import *
from .sensor import Sensor


class TemperatureSensor(Sensor):
    def __init__(self, controller, settings, logger, name, hwmon_object, auto_load=True):
        super().__init__(controller, settings, logger, name, hwmon_object, auto_load=auto_load)


    def format_value(self, value):
        return str(value) + "°C"