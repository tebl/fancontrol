import os
from abc import ABC, abstractmethod
from ..logger import LoggerMixin
from ..exceptions import SensorException, ConfigurationError
from .pwm_sensor import PWMSensor
from .fan import Fan


class BaseControl(ABC, LoggerMixin):
    BASE_PATH = '/sys/class/hwmon'


    def __init__(self, settings, logger, resolver, auto_load=True):
        self.settings = settings
        self.logger = logger
        self.resolver = resolver
        self.auto_load = auto_load
        self.fans = []
        self.sensors = {}
        self.outputs = {}
        self.object_resolver = None
        if self.auto_load:
            self.load()


    def get_path(self):
        return os.path.join(self.BASE_PATH, self.dev_base)


    def set_logger(self, logger):
        self.scheduler.set_logger(logger)
        for fan in self.fans:
            fan.set_logger(logger)
        for i, (name, sensor) in enumerate(self.sensors.items()):
            sensor.set_logger(logger)
        return super().set_logger(logger)


    def create_fan(self, name):
        return Fan(self, self.settings, self.logger, name)


    def create_sensor(self, fan, value, sensor_class):
        hwmon_object = self.resolve_object(value)
        if not hwmon_object:
            raise ConfigurationError('Value did not resolve to a valid object (value={})'.format(value), value)
        symbol_name = hwmon_object.get_symbol_name()
        sensor = None
        if symbol_name in self.sensors:
            sensor = self.sensors[symbol_name]
        else:
            self.log_debug('Creating Sensor({})'.format(value))
            sensor = sensor_class(
                self, 
                self.settings, 
                self.logger, 
                value, 
                hwmon_object
            )

            if sensor.require_writable() and not hwmon_object.is_writable():
                raise ConfigurationError('Writable sensor required (value={})'.format(value))
            if sensor.require_has_enable() and not hwmon_object.has_enable():
                raise ConfigurationError('Writable sensor with enable required (value={})'.format(value))

            self.sensors[symbol_name] = sensor
            if sensor_class is PWMSensor:
                self.outputs[symbol_name] = sensor
            
        sensor.register_fan(fan)
        return sensor


    def load(self):
        self.load_configuration()
        self.load_dependencies()
        self.load_fans()


    def load_configuration(self):
        self.delay = self.settings.delay
        if self.delay < 1:
            raise ConfigurationError("delay can't be less than 1", self.delay)
        self.__get_attribute('log_level')
        self.__get_attribute('dev_base')
        self.__get_attribute('dev_name')
        self.__get_attribute('dev_path')
        return True


    @abstractmethod
    def load_dependencies(self):
        '''
        Have controller load any dependencies needed in order to build a
        working setup. It should be called after load_configuration, but
        before loading fan definitions.
        '''
        ...
        self.__check_dev_base()
        return True

    
    def resolve_object(self, value):
        '''
        Get an object using the supplied value string
        '''
        return self.resolver.resolve_object(value, self.dev_base)

   
    def resolve_provider(self, value):
        '''
        '''
        return self.resolver.resolve_provider(value)



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
        dev_base = self.resolve_provider(self.settings.dev_base)
        if not dev_base:
            raise ConfigurationError('Setting "dev_base" did not resolve to a valid provider (value={})'.format(self.settings.dev_base), self.settings.dev_base)
        if not dev_base.check_driver_name(self.settings.dev_name):
            raise ConfigurationError('Setting "dev_name" did not match driver (value={})'.format(self.settings.dev_name), self.settings.dev_name)
        self.log_verbose('Setting "dev_name" ({}) appears OK'.format(self.settings.dev_name))
        if not dev_base.check_driver_path(self.settings.dev_path):
            raise ConfigurationError('Setting "dev_path" did not match driver (value={})'.format(self.settings.dev_path), self.settings.dev_path)
        self.log_verbose('Setting "dev_path" ({}) appears OK'.format(self.settings.dev_path))
        self.dev_base = dev_base
        self.log_verbose('Setting "dev_base" ({}) appears OK'.format(self.dev_base.get_title(include_summary=True)))


    def __str__(self):
        return self.__class__.__name__