from ..exceptions import *
from .sensor import Sensor


class TemperatureSensor(Sensor):
    def __init__(self, controller, settings, logger, name, device_path):
        super().__init__(controller, settings, logger, name, device_path)


    def get_value(self):
        if self.value == None:
            return None
        return self.value / 1000.0
    

    def format_value(self, value):
        return str(value) + "°C"