import os.path
from ..logger import LoggerMixin
from ..exceptions import SensorException, ConfigurationError
from .raw_sensor import RawSensor


class Sensor(RawSensor, LoggerMixin):
    def __init__(self, controller, settings, logger, name, device_path):
        super().__init__(logger, name, device_path)
        self.controller = controller
        self.settings = settings
        self.fans = []


    def update(self):
        '''
        Update sensor value, intended to be called at regular intervals. Note
        that this is the only point where values are actually updated, other
        methods work with stored values.

        NB! There is an occurrence of double-reads when first starting up, this
            is because fans may require sensor readings in order to select a
            suitable startup value.
        '''
        try:
            super().update()
        except SensorException as e:
            self.log_error('{} could not be updated ({})'.format(self, str(e)))


    def register_fan(self, fan):
        self.fans.append(fan)
