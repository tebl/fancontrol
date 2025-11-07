#!/usr/bin/python3

import sys
import argparse
import os
import time
from lib import Settings, PACKAGE, PACKAGE_NAME, utils
from lib.logger import *
from lib.exceptions import *
from lib.interrupt import InterruptHandler
from lib.pid_file import PIDFile
from lib.sensor import RawSensor
from lib.scheduler import MicroScheduler


class FanControl(LoggerMixin):
    def __init__(self, settings, logger):
        self.settings = settings
        self.logger = logger
        self.sensors = {}
        self.outputs = {}
        self.__read_configuration()
        self.running = False


    def control(self, interrupt_handler):
        self.running = True
        self.scheduler = MicroScheduler(self.logger, self.delay)

        self.log_info('{} starting'.format(self))
        self.__setup()
        while self.running:
            try:
                self.scheduler.set_next()
                self.__control()

                while self.running and not self.scheduler.was_passed():
                    if self.check_interrupt(interrupt_handler):
                        time.sleep(.3)
                        self.__u_control()
            except KeyboardInterrupt:
                self.running = False
        self.__shutdown()
        self.log_info('{} stopped'.format(self))


    def check_interrupt(self, handler):
        if handler.interrupted:
            self.log_warning('{} INT received, halting...'.format(self))
            self.running = False
        return self.running


    def __setup(self):
        self.log_verbose('{} setup'.format(self))
        try:
            self.__update_sensors()
            self.__setup_fans()
            self.__setup_pwm()
        except ControlRuntimeError as e:
            self.log_error('{} encountered during setup phase, halting...'.format(e))
            self.running = False
            self.__failsafe()


    def __failsafe(self):
        self.log_error('failsafe triggered, attempting to crash in a safe place')
        self.__shutdown(ignore_exceptions=True)


    def __setup_fans(self):
        for fan in self.fans:
            fan.setup()


    def __setup_pwm(self):
        for i, (name, sensor) in enumerate(self.sensors.items()):
            if type(sensor) is PWMSensor:
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
            output.plan_ahead()


    def __shutdown(self, ignore_exceptions = False):
        self.log_verbose('{} shutdown'.format(self))
        for method in [self.__shutdown_fans, self.__shutdown_pwm]:
            try:
                self.log_verbose('{} running {}...'.format(self, method.__name__))
                result = method(ignore_exceptions)
                self.log_verbose('{} ... {}'.format(self, result))
            except ControlRuntimeError as e:
                self.log_error('{} encountered {} during shutdown phase!'.format(self, e))


    def __shutdown_fans(self, ignore_exceptions = False):
        for fan in self.fans:
            fan.shutdown(ignore_exceptions)
        return 'OK'


    def __shutdown_pwm(self, ignore_exceptions = False):
        for i, (name, output) in enumerate(self.outputs.items()):
            output.shutdown(ignore_exceptions)
        return 'OK'


    def __str__(self):
        return FanControl.__name__


    def get_path(self):
        return os.path.join('/sys/class/hwmon', self.dev_base)


    def set_logger(self, logger):
        self.scheduler.set_logger(logger)
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
            if sensor_class is PWMSensor:
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


    def shutdown(self, ignore_exceptions=False):
        '''
        Called by FanControl when shutting down. As we don't really know
        anything about the underlying hardware at this level we'll just
        request that the fan be put on the hardware level and hope that
        the OutputSensor-class knows how to make better decisions.
        '''
        self.device.request_value(self, self.__to_request(self.pwm_max, self.pwm_max))


    def update(self):
        '''
        Called by FanControl during update cycles, somewhere at the start of
        it - immediately after updating sensors. At this point we're not
        writing any values directly, instead we're evaluating the current
        state and then requesting what we consider to be the next step.

        A negative value indicates that the fan should have been spinning,
        but isn't - the actual value is the value needed to spin it up again.
        '''
        self.device.request_value(self, self.__calculate())


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
                              (self.pwm_max - self.pwm_stop) /
                              (self.sensor_max - self.sensor_min) +
                              self.pwm_stop)

        # Check if the fan appears to have stopped. While ideally the above
        # calculation should keep the PWM-value above the level at which
        # the fan would physically seize, writing expression like this would
        # make it bit more clearer.
        if pwm_value > self.pwm_stop and self.pwm_input.get_value() == 0:
            return self.__to_request(self.pwm_start, pwm_value)
        return self.__to_request(pwm_value, pwm_value)


    def __to_request(self, requested, target):
        return [requested, target]


    def __str__(self):
        return 'Fan({})'.format(self.name)


    def __read_configuration(self):
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


class PWMSensor(Sensor):
    PWM_MIN = 0
    PWM_MAX = 255
    
    PWM_ENABLE_MANUAL = 1
    "Manual control, meaning that the user control its value"

    PWM_ENABLE_AUTO = 99
    "Automatic control, meaning that the underlying chipset control the value"

    STATE_STOPPED = 0
    STATE_STARTING = 1
    STATE_RUNNING = 2
    STATE_STOPPING = 3
    STATE_UNKNOWN = 99


    def __init__(self, controller, settings, logger, name, device_path):
        super().__init__(controller, settings, logger, name, device_path)
        self.original_enable = None
        self.enable_path = device_path + "_enable"
        self.state = self.STATE_UNKNOWN
        self.requests = []

        self.last_value = 0
        self.target_value = 0
        self.scheduler = None

        self.__check_configuration()


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
        match self.state:
            case self.STATE_STARTING:
                return self.__tick_from_starting()
            case self.STATE_STOPPING:
                return self.__tick_from_stopping()
            case self.STATE_RUNNING:
                return self.__tick_from_running()
        return False

    
    def __tick_from_starting(self, step_delay = 2):
        if self.scheduler == None:
            self.scheduler = MicroScheduler(self.logger, step_delay)
            return self.scheduler.set_next()
        
        if self.scheduler.was_passed():
            # Timer ran out, assume it started instead of doing sensibly things
            # like checking.
            self.__new_state(self.STATE_RUNNING)


    def __tick_from_stopping(self, step_delay = .5):
        if self.scheduler == None:
            self.scheduler = MicroScheduler(self.logger, step_delay)
            return self.scheduler.set_next()

        if self.scheduler.was_passed():
            if self.last_value == self.target_value:
                return self.__new_state(self.STATE_STOPPED)
            
            next_value = self.__next_step_value()
            self.log_verbose('{} stepping from {} to {} towards {}'.format(self, str(self.last_value), str(next_value), str(self.target_value)))
            self.last_value = next_value
            self.__write(self.device_path, self.name, self.last_value)
            return self.scheduler.set_next()


    def __tick_from_running(self, step_delay = .5):
        if self.scheduler == None:
            self.scheduler = MicroScheduler(self.logger, step_delay)
            return self.scheduler.set_next()

        if self.scheduler.was_passed():
            if self.last_value == self.target_value:
                return self.scheduler.set_next()
            
            next_value = self.__next_step_value()
            self.log_verbose('{} stepping from {} to {} towards {}'.format(self, str(self.last_value), str(next_value), str(self.target_value)))
            self.last_value = next_value
            self.__write(self.device_path, self.name, self.last_value)
            return self.scheduler.set_next()


    def __next_step_value(self, pwm_steps = 10):
        if self.last_value < self.target_value:
            return self.last_value + min([pwm_steps, abs(self.last_value - self.target_value)])
        if self.last_value > self.target_value:
            return self.last_value - min([pwm_steps, abs(self.last_value - self.target_value)])
        return self.last_value


    def __new_state(self, new_state):
        self.log_debug('{} setting new state {}'.format(self, self.__pwm_state_str(new_state)))
        self.state = new_state
        self.scheduler = None


    def plan_ahead(self):
        '''
        Apply some sort of algorithm before updating the actual PWM-values.
        '''
        self.log_verbose('{} updating'.format(self))
        match self.state:
            case self.STATE_STOPPED:
                return self.__plan_from_stopped()
            case self.STATE_RUNNING:
                return self.__plan_from_running()
            case _:
                self.log_error('{} encountered state {} during planning'.format(self, self.__pwm_state_str(self.state)))
                return False


    def __plan_from_stopped(self):
        '''
        A request is composed of two values; the first one is the value
        requested by the fan in order to get it spinning, or it is equal to
        the second. The second is the target value that we want to be at when
        stabilized.
        '''
        max_value = self.PWM_MIN
        max_target = self.PWM_MIN
        for (requester, values) in self.requests:
            requested, target = values
            largest = max(values)
            if largest > max_value:
                max_value = largest
            if target > max_target:
                max_target = target

        # The second part should not be needed, but kept for clarity.
        if max_value > 0 or max_target > 0:
            self.__set_starting(max_value, max_target)
        self.__discard_requests(warn_dropped=False)


    def __set_starting(self, pwm_start, pwm_target):
        if self.__write(self.device_path, self.name, pwm_start):
            self.__new_state(self.STATE_STARTING)
            self.target_value = pwm_target
            self.last_value = pwm_start


    def __plan_from_running(self):
        self.log_verbose('{} is planning for running'.format(self))
        self.last_value = self.get_value()
        self.target_value = self.__get_max_request()
        if (self.target_value == 0):
            self.__new_state(self.STATE_STOPPING)

        self.__discard_requests(warn_dropped=False)


    def request_value(self, requester, values):
        '''
        Called by fans in order to request a value, but at this point we're not
        actually doing anything except logging the request. Values will be only
        get updated when called by FanControl (see perform_update).
        '''
        requested, target = values
        self.log_verbose('{} requested {} from {}'.format(requester, max(values), self))
        self.requests.append((requester, values))


    def __discard_requests(self, warn_dropped = True):
        if self.requests and warn_dropped:
            for (requester, pwm_value) in self.requests:
                self.log_warning('{} discarding request ({} of {})'.format(self, requester, str(pwm_value)))
        self.requests = []


    def setup(self):
        '''
        Signal output sensor to turn on, this will be called after fans are
        instructed to request a sensible ititialization value. At this point
        we're expected to take control over fans, but should ensure that
        we've got a safe starting point.
        '''
        self.log_verbose('{} setup'.format(self))
        self.__discard_requests(warn_dropped=False)

        # Guess state based on current value
        self.state = self.STATE_STOPPED
        for fan in self.fans:
            if fan.pwm_input.get_value() > 0:
                self.log_debug('{} detected spinning {} reading {}'.format(self, fan, fan.pwm_input.get_value_str()))
                self.state = self.STATE_RUNNING
                break
        self.log_debug('{} state set to {}'.format(self, self.__pwm_state_str(self.state)))
        self.last_value = self.get_value()
        self.target_value = self.last_value

        self.read_original_enable()
        success = self.write_enable(self.PWM_ENABLE_MANUAL)
        self.log_info('{} set to {} control'.format(self, self.__pwm_mode_str(self.PWM_ENABLE_MANUAL)))
        return success


    def __pwm_mode_str(self, mode):
        match mode:
            case self.PWM_ENABLE_MANUAL:
                return "MANUAL"
            case self.PWM_ENABLE_AUTO:
                return "AUTO"
        return 'UNKNOWN({})'.format(str(mode))


    def __pwm_state_str(self, state):
        match state:
            case self.STATE_STOPPED:
                return "STOPPED"
            case self.STATE_STARTING:
                return "STARTING"
            case self.STATE_RUNNING:
                return "RUNNING"
            case self.STATE_STOPPING:
                return "STOPPING"
        return 'UNKNOWN({})'.format(str(state))


    def write_enable(self, value, ignore_exceptions = False):
        return self.__write(self.enable_path, self.name + '_enable', value, ignore_exceptions)


    def __write(self, path, name, pwm_value, ignore_exceptions = False):
        self.log_verbose('{} writing {} to {}'.format(self, str(pwm_value), name))        
        try:
            return self.write(path, pwm_value)
        except SensorException as e:
            if not ignore_exceptions:
                raise ControlRuntimeError('{} could not write {} to {} ({})'.format(self, pwm_value, name, e))
            self.log_warning('{} could not write {} to {} ({})'.format(self, pwm_value, name, e))
        return False


    def read_enable(self):
        try:
            return self.read_int(self.enable_path)
        except SensorException as e:
            raise ControlRuntimeError('{} could not read {}_enable'.format(self, self.name))


    def read_original_enable(self):
        self.original_enable = self.read_enable()
        self.log_debug('{} storing original {}_enable ({})'.format(self, self.name, str(self.original_enable)))


    def shutdown(self, ignore_exceptions = False):
        '''
        Signal output sensor to shut down, this is called immediately after
        fans are called to shut down with a suggested value in requests.
        '''
        self.log_verbose('{} shutdown'.format(self))
        if self.original_enable == None:
            self.log_warning('{} had no last_enable during shutdown'.format(self))
        else:
            if self.write_enable(self.original_enable, ignore_exceptions):
                self.log_info('{} returned to original control ({})'.format(self, self.__pwm_mode_str(self.original_enable)))
                self.__discard_requests(warn_dropped=False)
                return True
        
        if self.requests:
            value = self.__get_max_request()
            self.log_warning('{} could not return to original control ({}), setting it to {}'.format(self, self.__pwm_mode_str(self.original_enable), str(value)))
            if self.__write(self.device_path, self.name, value, ignore_exceptions):
                self.__discard_requests(warn_dropped=False)
                return True
            
        value = self.__get_max()
        self.log_error('{} could not set that either, but try with max value anyway ({})'.format(self, value))
        if not self.__write(self.device_path, self.name, value, ignore_exceptions):
            self.log_error('All attempts failed... hope everything works out for you :-)')

        # Clear requests - just in case we somehow bugged into starting up again
        self.__discard_requests(warn_dropped=False)
        return False


    def __get_max(self):
        '''
        Should probably check associated fans and get the max from there
        '''
        return max([fan.pwm_max for fan in self.fans], 
                   default=self.PWM_MAX)


    def __get_max_request(self):
        '''
        Get maximum from requested values, this ensures that we all always have
        sufficient power when controlling multiple fans.
        '''
        return max([max(values) for (requester, values) in self.requests], default=self.PWM_MIN)


    def __check_configuration(self):
        if not os.path.isfile(self.enable_path):
            raise ConfigurationError('{}.{} not found'.format(self, 'enable_path'), self.enable_path)
        self.log_verbose('{}.{} input OK'.format(self, 'enable_path', self.device_path))


class TemperatureSensor(Sensor):
    def __init__(self, controller, settings, logger, name, device_path):
        super().__init__(controller, settings, logger, name, device_path)


    def get_value(self):
        if self.value == None:
            return None
        return self.value / 1000.0
    

    def get_value_str(self):
        return super().get_value_str() + "°C"


class FanSensor(Sensor):
    def __init__(self, controller, settings, logger, name, device_path):
        super().__init__(controller, settings, logger, name, device_path)

    
    def get_value_str(self):
        return super().get_value_str() + " RPM"


def is_config(config_path):
    '''
    Check that the specified configuration file actually exists and has the
    right extension, but beyond that we're not looking at the contents of it.
    '''
    if not os.path.isfile(config_path):
        raise argparse.ArgumentError(utils.to_keypair_str('No suitable file specified', config_path))
    if not config_path.lower().endswith(('.ini')):
        raise argparse.ArgumentError(utils.to_keypair_str('Unknown extension specified', config_path))
    return config_path


def is_pid(pid_path):
    '''
    Check that the specified configuration file actually exists and has the
    right extension, but beyond that we're not looking at the contents of it.
    '''
    if not pid_path.lower().endswith(('.pid')):
        raise argparse.ArgumentError(utils.to_keypair_str('Unknown extension specified', pid_path))
    return pid_path


def perform_verify(run_verify, logger, settings):
    '''
    Loads up the configuration then returns, this hopefully will allow us to
    check if the runtime environment is somewhat sane before doing something
    as insane as for instance stopping the CPU-fan. 
    '''
    if not run_verify:
        return False

    try:
        logger.log(PACKAGE)
        FanControl(settings, logger)
        logger.log('OK.')
    except ConfigurationError as e:
        logger.log(str(e), Logger.ERROR)
        sys.exit(1)
    return True


def get_filter_level(setting, set_debug, set_verbose):
    levels = [ Logger.to_filter_value(setting) ]
    if set_debug:
        levels.append(Logger.DEBUG)
    if set_verbose:
        levels.append(Logger.VERBOSE)
    return max(levels)


def reconfigure_logger(args, logger, filter_level, settings):
    if args.log_console:
        logger.set_filter(filter_level)
    elif args.log_journal:
        logger = JournalLogger(PACKAGE_NAME, filter_level)
    elif args.log_logformat:
        logger = LogfileLogger(PACKAGE_NAME, filter_level)
    else:
        match settings.log_using:
            case Logger.JOURNAL:
                logger = JournalLogger(PACKAGE_NAME, filter_level)
            case Logger.LOG_FILE:
                logger = LogfileLogger(PACKAGE_NAME, filter_level)
            case Logger.CONSOLE:
                logger.set_filter(filter_level)
            case _:
                logger.log(utils.to_keypair_str('Encountered unknown logger value', settings.log_using), Logger.WARNING)

    if isinstance(logger, FormattedLogger):
        features = settings.log_formatter
        if args.monochrome:
            features = ANSIFormatter.MONOCHROME
        if args.less_colours:
            features = ANSIFormatter.BASIC
        if args.more_colours:
            features = ANSIFormatter.EXPANDED
        logger.set_formatter(ANSIFormatter(features))

    return logger


def get_logger(logger, args, settings):
    filter_level = get_filter_level(settings.log_level, args.debug, args.verbose)
    logger = reconfigure_logger(args, logger, filter_level, settings)
    logger.log('Initialized ' + str(logger), Logger.DEBUG)
    return logger


def main():
    parser = argparse.ArgumentParser()
    parser.description = 'Python fancontrol, spinning fans in the 21st century'
    parser.add_argument('-c', '--config-path', type=is_config, default='fancontrol.ini', help='Specify configuration')
    parser.add_argument('-v', '--version', action='version', version=PACKAGE, help="Show version information")
    parser.add_argument('--pid-file', type=is_pid, default='fancontrol.pid', help='Specify pid path')
    parser.add_argument('-z', '--zap-pid', action='store_true', help='Remove pid if it exists')
    parser.add_argument('--verify', action='store_true', help='Fancontrol will load and check configuration before exiting')
    parser_logging = parser.add_mutually_exclusive_group()
    parser_logging.add_argument('--log-console', action='store_true', help='Fancontrol will only log to console')
    parser_logging.add_argument('--log-logformat', action='store_true', help='Logs are printed, but now in with timestamps')
    parser_logging.add_argument('--log-journal', action='store_true', help='Logs are sent to systemd-journal')
    parser.add_argument('--debug', action='store_true', help='Enable debug messages')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose debug messages')
    parser_colorization = parser.add_mutually_exclusive_group()
    parser_colorization.add_argument('--monochrome', action='store_true', help='Remove colorization from output')
    parser_colorization.add_argument('--less-colours', action='store_true', help='Limit colorization to 16 colours')
    parser_colorization.add_argument('--more-colours', action='store_true', help='Allow colorization to use 256 colours')
    args = parser.parse_args()

    try:
        current_logger = ConsoleLogger(PACKAGE_NAME)
        settings = Settings(args.config_path, current_logger)

        # If we're only running a verification of the configuration
        if perform_verify(args.verify, current_logger, settings):
            sys.exit(0)

        # From this point on the assumption is that we are no longer running
        # interactively. First step is to switch to a more suitable logger.
        current_logger = get_logger(current_logger, args, settings)

        with PIDFile(current_logger, args.pid_file, zap_if_exists=args.zap_pid):
            fancontrol = FanControl(settings, current_logger)
            with InterruptHandler() as handler:
                fancontrol.control(handler)
    except ControlException as e:
        current_logger.log(str(e), Logger.ERROR)
        sys.exit(1)


if __name__ == "__main__":
    main()
