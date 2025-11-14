import os
from ..logger import LoggerMixin
from ..exceptions import SensorException, ConfigurationError
from .pwm_sensor import PWMSensor
from .fan import Fan


class BaseControl(LoggerMixin):
    def __init__(self, settings, logger, auto_load=True):
        self.settings = settings
        self.logger = logger
        self.auto_load = auto_load
        self.fans = []
        self.sensors = {}
        self.outputs = {}
        if self.auto_load:
            self.load_configuration()
            self.load_fans()


    def get_path(self):
        return os.path.join('/sys/class/hwmon', self.dev_base)


    def set_logger(self, logger):
        self.scheduler.set_logger(logger)
        for fan in self.fans:
            fan.set_logger(logger)
        for i, (name, sensor) in enumerate(self.sensors.items()):
            sensor.set_logger(logger)
        return super().set_logger(logger)


    def create_fan(self, name):
        return Fan(self, self.settings, self.logger, name)


    def create_sensor(self, fan, name, sensor_class):
        device_path = os.path.join(self.get_path(), name)
        sensor = None
        if device_path in self.sensors:
            sensor = self.sensors[device_path]
        else:
            self.log_debug('Creating Sensor({})'.format(name))
            sensor = sensor_class(
                self, 
                self.settings, 
                self.logger, 
                name, 
                device_path
            )
            self.sensors[device_path] = sensor
            if sensor_class is PWMSensor:
                self.outputs[device_path] = sensor
            
        sensor.register_fan(fan)
        return sensor


    def load_configuration(self):
        self.delay = self.settings.delay
        if self.delay < 1:
            raise ConfigurationError("delay can't be less than 1", self.delay)
        self.__get_attribute('log_level')

        self.__get_attribute('dev_base')
        self.__check_dev_base()

        self.__get_attribute('dev_name')
        self.__check_dev_name()

        self.__get_attribute('dev_path')
        self.__check_dev_path()
        return True
    

    def load_fans(self):
        self.__load_fans()
        if not self.fans:
            if self.settings.error_on_empty:
                raise ConfigurationError('No enabled fans!')
            self.log_warning('No enabled fans!')
        return True


    def __load_fans(self):
        self.fans = []
        for name in self.settings.sections():
            self.log_debug('Creating Fan({})'.format(name))
            self.fans.append( self.create_fan(name) )


    def __get_attribute(self, attr):
        value = self.settings.get('Settings', attr)
        if not value:
            raise ConfigurationError('Setting "{}" has not been set'.format(attr), value)
        self.log_verbose('{}.{} = {}'.format(self.__class__.__name__, attr, value))
        setattr(self, attr, value)


    def __check_dev_base(self):
        device_path = self.get_path()
        if not os.path.isdir(device_path):
            raise ConfigurationError('Setting "dev_base" ({}) does not match existing path'.format(self.dev_base), device_path)
        self.log_verbose('Setting "dev_base" ({}) appears OK'.format(device_path))


    def __check_dev_name(self):
        '''
        Safety check to ensure that the configured hwmonX driver name matches
        the one specified in the configuration. 
        '''
        file_path = os.path.join(self.get_path(), 'name')
        if not os.path.isfile(file_path):
            raise ConfigurationError('Path does not exist', file_path)
        with open(file_path, 'r') as file:
            content = file.read()
            content = content.strip()
            if content == self.dev_name:
                self.log_verbose('Setting "dev_name" ({}) appears OK'.format(file_path))
            else:
                raise ConfigurationError('Device name did not match configuration', self.dev_name)


    def __check_dev_path(self):
        '''
        Safety check to ensure that the configured dev_path matches the kernel
        link listed as hwmonX/device matches. If it doesn't then devices may
        have changed since creating the configuration.
        '''
        device_path = os.path.join(self.get_path(), 'device')
        linked_path = os.path.realpath(device_path)

        config_path = self.dev_path
        if config_path[0] != os.sep:
            config_path = os.path.join('/sys', config_path)

        if config_path == linked_path:
            self.log_verbose('Setting "dev_path" ({}) appears OK'.format(linked_path))
        else:
            raise ConfigurationError('Path {} did not resolve to {}'.format(device_path, config_path))


    def __str__(self):
        return self.__class__.__name__