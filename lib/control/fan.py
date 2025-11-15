import os.path
from ..logger import LoggerMixin
from ..exceptions import *
from .pwm_request import PWMRequest
from .fan_sensor import FanSensor
from .pwm_sensor import PWMSensor
from .temperature_sensor import TemperatureSensor


class Fan(LoggerMixin):
    PWM_MIN = 0
    PWM_MAX = 255


    def __init__(self, controller, settings, logger, name, auto_load=True):
        self.controller = controller
        self.settings = settings
        self.logger = logger
        self.name = name
        if auto_load:
            self.load_configuration()
        self.log_debug('{} initialized OK'.format(self))


    def setup(self):
        '''
        Called by FanControl when starting up, and as a starting point we'll
        just make a suggestion of a suitable place to start.
        '''
        self.device.request_value(self.__calculate())


    def shutdown(self, ignore_exceptions=False):
        '''
        Called by FanControl when shutting down. As we don't really know
        anything about the underlying hardware at this level we'll just
        request that the fan be put on the hardware level and hope that
        the OutputSensor-class knows how to make better decisions.
        '''
        self.device.request_value(
            PWMRequest(self, target_value=self.pwm_max, start_value=self.pwm_max)
        )


    def update(self):
        '''
        Called by FanControl during update cycles, somewhere at the start of
        it - immediately after updating sensors. At this point we're not
        writing any values directly, instead we're evaluating the current
        state and then requesting what we consider to be the next step.
        '''
        self.device.request_value(self.__calculate())


    def __calculate(self):
        '''
        Calculate the pwm_value to request from output. The rationale is that
        unless we hit the lower and upper bounds, then we're mapping from
        temperatures to actual PWM-values.
        '''
        temp = self.sensor.get_value()

        pwm_value = self.pwm_min
        if temp <= self.sensor_min:
            pwm_value = self.pwm_min
        elif temp >= self.sensor_max:
            pwm_value = self.pwm_max
        else:
            pwm_value = round((temp - self.sensor_min) * 
                              (self.pwm_max - self.pwm_min) /
                              (self.sensor_max - self.sensor_min) +
                              self.pwm_min)

        # Check if the fan appears to have stopped. Ideally the above
        # calculation should keep the PWM-value above the level at which
        # the fan would physically seize.
        if pwm_value > self.pwm_stop and self.pwm_input.get_value() == 0:
            self.log_verbose('{} appears to have stopped!'.format(self))
            return PWMRequest(self, target_value=pwm_value, start_value=self.pwm_start)
        return PWMRequest(self, target_value=pwm_value)


    def get_title(self, include_summary=False):
        if not include_summary:
            return self.name
        return '{} (device={}, sensor={}, pwm_input={})'.format(self.name, self.device.get_title(), self.sensor.get_title(), self.pwm_input.get_title())


    def __str__(self):
        return 'Fan({})'.format(self.name)


    def load_configuration(self):
        if not self.name:
            raise ConfigurationError('Malformed fan name', self.name)
        if not self.settings.have_section(self.name):
            raise ConfigurationError('Fan configuration not found', self)
        
        self.enabled = self.settings.is_enabled(self.name, 'enabled')

        self.__get_attribute('device')
        self.device = self.controller.create_sensor(self, self.device, PWMSensor)
        self.log_verbose('{}.{} resolved to {}'.format(self, 'device', self.device))

        self.__get_attribute('sensor')
        self.sensor = self.controller.create_sensor(self, self.sensor, TemperatureSensor)
        self.log_verbose('{}.{} resolved to {}'.format(self, 'sensor', self.sensor))

        self.__get_attribute_int('sensor_min')
        self.__get_attribute_int('sensor_max')
        if self.sensor_min >= self.sensor_max:
            raise ConfigurationError('Setting "sensor_min" ({}) must be lower than "pwm_max" ({})'.format(self.sensor_min, self.sensor_max), self)

        self.__get_attribute('pwm_input')
        self.pwm_input = self.controller.create_sensor(self, self.pwm_input, FanSensor)
        self.log_verbose('{}.{} resolved to {}'.format(self, 'pwm_input', self.pwm_input))

        self.__get_attribute_int('pwm_min', min_value=Fan.PWM_MIN)
        self.__get_attribute_int('pwm_max', max_value=Fan.PWM_MAX)

        self.__get_attribute_int('pwm_start', min_value=Fan.PWM_MIN)
        self.__get_attribute_int('pwm_stop', max_value=Fan.PWM_MAX)
        if self.pwm_stop >= self.pwm_max:
            raise ConfigurationError('Setting "pwm_stop" ({}) must be lower than "pwm_max" ({})'.format(self.pwm_stop, self.pwm_max), self)
        if self.pwm_stop < self.pwm_min:
            raise ConfigurationError('Setting "pwm_stop" ({}) must be larger than "pwm_min" ({})'.format(self.pwm_stop, self.pwm_min), self)
            

    def __get_attribute(self, attr):
        value = self.settings.get(self.name, attr)
        if not value:
            raise ConfigurationError('Setting "{}" has not been set'.format(attr), self)
        self.log_verbose('{}.{} = {}'.format(self, attr, value))
        setattr(self, attr, value)


    def __get_attribute_int(self, attr, min_value=None, max_value=None):
        value = self.settings.getint(self.name, attr)
        if min_value != None:
            if value < min_value:
                raise ConfigurationError('Setting "{}" must be at least {}'.format(attr, min_value), self)
        if max_value != None:
            if value > max_value:
                raise ConfigurationError('Setting "{}" must not exceed {}'.format(attr, max_value), self)
        self.log_verbose('{}.{} = {}'.format(self, attr, value))
        setattr(self, attr, value)