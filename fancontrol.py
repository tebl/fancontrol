#!/usr/bin/python3

import sys
import argparse
import os
import time
from lib import Settings, PACKAGE_VERSION
from lib.logger import *
from pprint import pprint


class FanControl(LoggerMixin):
    def __init__(self, settings, logger):
        self.settings = settings
        self.logger = logger
        self.sensors = {}
        self.outputs = {}
        self.__read_configuration()
        self.running = False


    def control(self):
        self.running = True

        self.log_info('{} starting'.format(self))
        self.__setup()
        while self.running:
            try:
                self.next_tick = time.time() + self.delay
                self.__control()

                while self.running and time.time() < self.next_tick:
                    time.sleep(.3)
                    self.__u_control()
            except KeyboardInterrupt:
                self.running = False
        self.__shutdown()
        self.log_info('{} stopped'.format(self))


    def __setup(self):
        self.log_verbose('{} setup'.format(self))
        try:
            self.__update_sensors()
            self.__setup_fans()
            self.__setup_pwm()
        except RuntimeError as e:
            self.log_error('{} encountered during setup phase, halting...'.format(e))
            self.running = False
            self.__failsafe()


    def __failsafe(self):
        self.log_error('failsafe triggered, attempting to crash in a safe place')
        self.__shutdown()


    def __setup_fans(self):
        for fan in self.fans:
            fan.setup()


    def __setup_pwm(self):
        for i, (name, sensor) in enumerate(self.sensors.items()):
            if type(sensor) is OutputSensor:
                sensor.setup()


    def __control(self):
        '''
        Called once at the start of every update cycle, takes care of updating
        and then allowing each component to plan their next move.
        '''
        self.__update_sensors()
        self.__update_fans()
        self.__control_done()


    def __u_control(self):
        for i, (name, sensor) in enumerate(self.outputs.items()):
            sensor.u_tick()


    def __update_sensors(self):
        for i, (name, sensor) in enumerate(self.sensors.items()):
            sensor.update()


    def __update_fans(self):
        for fan in self.fans:
            fan.update()


    def __control_done(self):
        for i, (name, output) in enumerate(self.outputs.items()):
            output.perform_update()


    def __shutdown(self):
        self.log_verbose('{} shutdown'.format(self))
        for method in [self.__shutdown_fans, self.__shutdown_pwm]:
            try:
                self.log_verbose('{} running {}...'.format(self, method.__name__))
                result = method()
                self.log_verbose('{} ... {}'.format(self, result))
            except RuntimeError as e:
                self.log_error('{} encountered {} during shutdown phase!'.format(self, e))


    def __shutdown_fans(self):
        for fan in self.fans:
            fan.shutdown()
        return 'OK'


    def __shutdown_pwm(self):
        for i, (name, output) in enumerate(self.outputs.items()):
            output.shutdown()
        return 'OK'


    def __str__(self):
        return FanControl.__name__


    def get_path(self):
        return os.path.join('/sys/class/hwmon', self.dev_base)


    def set_logger(self, logger):
        for fan in self.fans:
            fan.set_logger(logger)
        for i, (name, sensor) in enumerate(self.sensors.items()):
            sensor.set_logger(logger)
        return super().set_logger(logger)


    def __read_configuration(self):
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

        self.__load_fans()
        if not self.fans:
            if self.settings.error_on_empty:
                raise ConfigurationError('No enabled fans!')
            self.log_warning('No enabled fans!')


    def __check_dev_base(self):
        device_path = self.get_path()
        if os.path.isdir(device_path):
            self.log_verbose('Setting "dev_base" ({}) appears OK'.format(device_path))
        else:
            raise ConfigurationError('Setting "dev_base" ({}) does not match existing path'.format(self.dev_base), device_path)


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


    def __get_attribute(self, attr):
        value = self.settings.get('Settings', attr)
        if not value:
            raise ConfigurationError('Setting "{}" has not been set'.format(attr), value)
        self.log_verbose('{}.{} = {}'.format(FanControl.__name__, attr, value))
        setattr(self, attr, value)


    def __load_fans(self):
        self.fans = []
        for name in self.settings.sections():
            self.log_debug('Creating Fan({})'.format(name))
            self.fans.append( self.create_fan(name) )
    

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
            if sensor_class is OutputSensor:
                self.outputs[device_path] = sensor
            
        sensor.register_fan(fan)
        return sensor


class Fan(LoggerMixin):
    PWM_MIN = 0
    PWM_MAX = 255


    def __init__(self, controller, settings, logger, name):
        self.controller = controller
        self.settings = settings
        self.logger = logger
        self.name = name
        self.__read_configuration()
        self.log_debug('{} initialized OK'.format(self))


    def setup(self):
        '''
        Called by FanControl when starting up, and as a starting point we'll
        just make a suggestion of a suitable place to start.
        '''
        self.device.request_value(self, self.__calculate())


    def shutdown(self):
        '''
        Called by FanControl when shutting down. As we don't really know
        anything about the underlying hardware at this level we'll just
        request that the fan be put on the hardware level and hope that
        the OutputSensor-class knows how to make better decisions.
        '''
        self.device.request_value(self, self.pwm_max)


    def update(self):
        '''
        Called by FanControl during update cycles, somewhere at the start of
        it - immediately after updating sensors. At this point we're not
        writing any values directly, instead we're evaluating the current
        state and then requesting what we consider to be the next step.
        '''
        self.device.request_value(self, self.__calculate())


    def __calculate(self):
        temp = self.sensor.read()

        if temp < self.sensor_min:
            return self.pwm_min
        if temp > self.sensor_max:
            return self.pwm_max
        return round(
            self.PWM_MIN +
            (float(temp - self.sensor_min) /
            float(self.sensor_max - self.sensor_min)) *
            (self.PWM_MAX - self.PWM_MIN)
        )


    def __str__(self):
        return 'Fan({})'.format(self.name)


    def __read_configuration(self):
        if not self.name:
            raise ConfigurationError('Malformed fan name', self.name)
        if not self.settings.have_section(self.name):
            raise ConfigurationError('Fan configuration not found', self)
        
        self.enabled = self.settings.is_enabled(self.name, 'enabled')

        self.__get_attribute('device')
        self.device = self.controller.create_sensor(self, self.device, OutputSensor)
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


class Sensor(LoggerMixin):
    def __init__(self, controller, settings, logger, name, device_path):
        self.controller = controller
        self.settings = settings
        self.logger = logger
        self.name = name
        self.device_path = device_path
        self.fans = []
        self.__check_configuration()


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
            self.value = self.read_direct(self.device_path)
            self.log_verbose('{} = {}'.format(self, self.get_value()))
        except ValueError as e:
            self.log_error('{} could not be updated ({})'.format(self, str(e)))
        except FileNotFoundError as e:
            self.log_error('{} could not be updated ({})'.format(self, str(e)))


    def read_direct(self, sensor_path):
        with open(sensor_path, 'r') as file:
            data = file.read()
            return int(data)


    def read(self):
        '''
        Returns the last read sensor value
        '''
        return self.value


    def get_value(self):
        '''
        Returns the last read sensor value as a string, formatted for output
        with relevant unit designation.
        '''
        return str(self.read())


    def register_fan(self, fan):
        self.fans.append(fan)


    def __str__(self):
        return '{}({})'.format(self.__class__.__name__, self.name)


    def __check_configuration(self):
        if not os.path.isfile(self.device_path):
            raise ConfigurationError('{}.{} not found'.format(self, 'device_path'), self.device_path)
        self.log_verbose('{}.{} input OK'.format(self, 'device_path', self.device_path))


class OutputSensor(Sensor):
    PWM_MIN = 0
    PWM_MAX = 255
    PWM_ENABLE_MANUAL = 1
    PWM_ENABLE_AUTO = 99


    def __init__(self, controller, settings, logger, name, device_path):
        super().__init__(controller, settings, logger, name, device_path)
        self.last_enable = None
        self.enable_path = device_path + "_enable"
        self.__check_configuration()
        self.requests = []


    def update(self):
        '''
        The start of every update cycle begins with  an update to every sensor.
        This includes OutputSensor as we're this will also read the current
        PWM-value (0-255).
        '''
        super().update()
        self.__discard_requests()
    

    def u_tick(self):
        '''
        The period between update cycles are split up into micro-ticks, duration
        not guaranteed. If we need something to change gradually over time, this
        is the place to do it.
        '''
        pass


    def request_value(self, requester, pwm_value):
        '''
        Called by fans in order to request a value, but at this point we're not
        actually doing anything except logging the request. Values will be only
        get updated when called by FanControl (see perform_update).
        '''
        self.log_verbose('{} requested {} from {}'.format(requester, str(pwm_value), self))
        self.requests.append((requester, pwm_value))


    def perform_update(self):
        '''
        Apply some sort of algorithm before updating the actual PWM-values.
        '''
        self.log_debug('{} updating'.format(self))


    def __discard_requests(self):
        if self.requests:
            for (requester, pwm_value) in self.requests:
                self.log_warning('{} discarding request ({} of {})'.format(self, requester, str(pwm_value)))
        self.requests = []


    def __write(self, pwm_value):
        self.log_verbose('{} write'.format(self, str(pwm_value)))
        #  echo pwm_value > pwmX
        pass


    def setup(self):
        '''
        Signal output sensor to turn on, this will be called after fans are
        instructed to request a sensible ititialization value. At this point
        we're expected to take control over fans, but should ensure that
        we've got a safe starting point.
        '''
        # if not self.requests:
        #     self.log_warning('{} attempting setup (no fan suggestions)'.format(self))
        # self.log_warning(str(self.get_value()))
        self.log_verbose('{} setup'.format(self))
        # echo 1 > pwmX_enable


        self.read_last_enable()

        pass


    def set_enable(self):
        pass


    def read_enable(self):
        try:
            return self.read_direct(self.enable_path)
        except (FileNotFoundError, ValueError) as e:
            raise RuntimeError('{} could not read {}_enable'.format(self, self.name))


    def read_last_enable(self):
        self.last_enable = self.read_enable()
        self.log_debug('{} storing last {}_enable ({})'.format(self, self.name, str(self.last_enable)))


    def shutdown(self):
        '''
        Signal output sensor to shut down, this is called immediately after
        fans are called to shut down (ending with a suggested value).
        '''
        self.log_verbose('{} shutdown'.format(self))
        # echo 99 > pwmX_enable
        pass

    
    def __check_configuration(self):
        if not os.path.isfile(self.enable_path):
            raise ConfigurationError('{}.{} not found'.format(self, 'enable_path'), self.enable_path)
        self.log_verbose('{}.{} input OK'.format(self, 'enable_path', self.device_path))


class TemperatureSensor(Sensor):
    def __init__(self, controller, settings, logger, name, device_path):
        super().__init__(controller, settings, logger, name, device_path)


    def read(self):
        if self.value == None:
            return None
        return self.value / 1000.0
    

    def get_value(self):
        return super().get_value() + "°C"


class FanSensor(Sensor):
    def __init__(self, controller, settings, logger, name, device_path):
        super().__init__(controller, settings, logger, name, device_path)

    
    def get_value(self):
        return super().get_value() + " RPM"


class ConfigurationError(Exception):
    def __init__(self, message, details = None):
        if details:
            super().__init__(Logger.to_key_value(message, details))
        else:
            super().__init__(message)


class RuntimeError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


    def __str__(self):
        return '{}({})'.format(self.__class__.__name__, self.message)


def is_config(config_path):
    '''
    Check that the specified configuration file actually exists and has the
    right extension, but beyond that we're not looking at the contents of it.
    '''
    if not os.path.isfile(config_path):
        raise argparse.ArgumentError(Logger.to_key_value('No suitable file specified', config_path))
    if not config_path.lower().endswith(('.ini')):
        raise argparse.ArgumentError(Logger.to_key_value('Unknown extension specified', config_path))
    return config_path


def perform_verify(run_verify, logger, settings):
    '''
    Loads up the configuration then returns, this hopefully will allow us to
    check if the runtime environment is somewhat sane before doing something
    as insane as for instance stopping the CPU-fan. 
    '''
    if not run_verify:
        return False

    try:
        logger.log(PACKAGE_VERSION)
        FanControl(settings, logger)
        logger.log('OK.')
    except ConfigurationError as e:
        logger.log(str(e), Logger.ERROR)
        sys.exit(1)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.description = 'Python fancontrol, spinning fans in the 21st century'
    parser.add_argument('-c', '--config-path', type=is_config, default='fancontrol.ini', help='Specify configuration')
    parser.add_argument('-v', '--version', action='version', version=PACKAGE_VERSION, help="Show version information")
    parser.add_argument('--verify', action='store_true', help='Fancontrol will load and check configuration before exiting')
    args = parser.parse_args()

    logger = ConsoleLogger()
    settings = Settings(args.config_path, logger)

    # If we're only running a verification of the configuration
    if perform_verify(args.verify, logger, settings):
        sys.exit(0)

    # From this point on the assumption is that we are no longer running
    # interactively. First step is to switch to a more suitable logger.
    logger = LogfileLogger(settings.log_level)
    logger.log('Initialized ' + str(logger), Logger.DEBUG)

    try:
        fancontrol = FanControl(settings, logger)
        fancontrol.control()
    except ConfigurationError as e:
        logger.log(str(e), Logger.ERROR)
        sys.exit(1)


if __name__ == "__main__":
    main()
