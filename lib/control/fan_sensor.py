from ..exceptions import *
from .sensor import Sensor


class FanSensor(Sensor):
    def __init__(self, controller, settings, logger, name, device_path):
        super().__init__(controller, settings, logger, name, device_path)

    
    def format_value(self, value):
        return str(value) + " RPM"
    

    def peek_running(self):
        '''
        This allows FanControl to have a peek at the sensor value between
        regular update cycles without updating values used during planning.
        
        Any possible SensorException will be logged as a warning, letting
        FanControl deal with such an error if it crops up during planning.
        '''
        try:
            return self.read_int(self.device_path) > 0
        except SensorException as e:
            self.log_warning('{}.peek_running encountered a sensor read failure ({})'.format(self, e))
        return False