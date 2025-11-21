import os.path
from ..logger import LoggerMixin
from ..exceptions import *
from ..scheduler import MicroScheduler
from .sensor import Sensor
from .pwm_request import PWMRequest


class PWMSensor(Sensor):
    '''
    Implements a PWM-sensor operating with values from 0 through 255. As one
    or more fans can be controlled through this single value, most of the
    control logic will be found within this class.
    '''
    PWM_MIN = 0
    PWM_MAX = 255

    ENABLE_SUFFIX = '_enable'
    
    PWM_ENABLE_MANUAL = 1
    "Manual control, meaning that the user control its value"

    PWM_ENABLE_AUTO = 99
    "Automatic control, meaning that the underlying chipset control the value"

    STATE_STOPPED = 0
    STATE_STARTING = 1
    STATE_RUNNING = 2
    STATE_STOPPING = 3
    STATE_UNKNOWN = 99


    def __init__(self, controller, settings, logger, name, device_path, auto_load=True):
        super().__init__(controller, settings, logger, name, device_path, auto_load=auto_load)
        self.original_enable = None
        self.enable_path = device_path + self.ENABLE_SUFFIX
        self.state = self.STATE_UNKNOWN
        self.requests = []

        self.last_value = 0
        self.target = 0
        self.scheduler = None


    def get_title(self, include_summary=False):
        if not include_summary:
            return super().get_title(include_summary=False)
        return '{} (value={}, enable={})'.format(
            self.name,
            str(self.format_value(self.read_int(self.device_path))),
            str(self.__pwm_mode_str(self.read_enable()))
        )


    def update(self):
        '''
        The start of every update cycle begins with  an update to every sensor.
        This also includes this class, this will read the current PWM-value
        (0-255).
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

    
    def __tick_from_starting(self, step_delay=1):
        if self.scheduler == None:
            self.scheduler = MicroScheduler(self.logger, step_delay, limit=5)
            return self.scheduler.set_next()
        
        if self.scheduler.was_passed():
            not_started = []
            for fan in self.fans:
                if not fan.pwm_input.peek_running():
                    not_started.append(fan)

            try:
                if not_started:
                    for fan in not_started:
                        self.log_verbose('{} waiting for {} to start...'.format(self, fan))
                    return self.scheduler.set_next()
                self.__new_state(self.STATE_RUNNING)
            except SchedulerLimitExceeded as e:
                for fan in not_started:
                    self.log_error('{} gave up on waiting for {} to start...'.format(self, fan))
                self.__new_state(self.STATE_RUNNING)
                

    def __tick_from_stopping(self, step_delay = .5):
        if self.scheduler == None:
            self.scheduler = MicroScheduler(self.logger, step_delay)
            return self.scheduler.set_next()

        if self.scheduler.was_passed():
            if self.last_value == self.target:
                return self.__new_state(self.STATE_STOPPED)
            
            next_value = self.__next_step_value()
            self.log_verbose('{} stepping from {} to {} towards {}'.format(self, str(self.last_value), str(next_value), str(self.target)))
            self.last_value = next_value
            self.__write(self.device_path, self.name, self.last_value)
            return self.scheduler.set_next()


    def __tick_from_running(self, pwm_steps=20):
        if self.scheduler == None:
            self.scheduler = MicroScheduler(
                self.logger, 
                MicroScheduler.suggest_step_delay(
                    cycle_length=self.controller.delay,
                    max_steps=self.PWM_MAX/pwm_steps,
                    max_length=2
                )
            )
            return self.scheduler.set_next()

        if self.scheduler.was_passed():
            if self.last_value == self.target:
                return self.scheduler.set_next()
            
            next_value = self.__next_step_value(pwm_steps)
            self.log_verbose('{} stepping from {} to {} towards {}'.format(self, str(self.last_value), str(next_value), str(self.target)))
            self.last_value = next_value
            self.__write(self.device_path, self.name, self.last_value)
            return self.scheduler.set_next()


    def __next_step_value(self, pwm_steps=20):
        if self.last_value < self.target:
            return self.last_value + min([pwm_steps, abs(self.last_value - self.target)])
        if self.last_value > self.target:
            return self.last_value - min([pwm_steps, abs(self.last_value - self.target)])
        return self.last_value


    def __new_state(self, new_state):
        self.log_debug('{} setting new state {}'.format(self, self.__pwm_state_str(new_state)))
        self.state = new_state
        self.scheduler = None
        return True
    

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
        rq_max_start, rq_max_target = PWMRequest.get_max(self.requests)

        if rq_max_target is not None and rq_max_target.target_value > max_value:
            max_value = rq_max_target.target_value
        if rq_max_start is not None and rq_max_start.start_value > max_value:
            max_value = rq_max_start.start_value

        if rq_max_start:
            self.__set_starting(max_value, rq_max_target.target_value)
        self.__discard_requests(warn_dropped=False)


    def __set_starting(self, pwm_start, pwm_target):
        if self.__write(self.device_path, self.name, pwm_start):
            self.__new_state(self.STATE_STARTING)
            self.target = pwm_target
            self.last_value = pwm_start


    def __plan_from_running(self):
        self.log_verbose('{} is planning for running'.format(self))
        self.last_value = self.get_value()
        target = PWMRequest.get_max_target(self.requests)
        if target is not None:
            self.target = target
        if (self.target == 0):
            self.__new_state(self.STATE_STOPPING)

        self.__discard_requests(warn_dropped=False)


    def request_value(self, request):
        '''
        Called by fans in order to request a value, but at this point we're not
        actually doing anything except logging the request. Values will be only
        get updated when called by FanControl (see perform_update).
        '''
        self.log_verbose('{} was requested {}'.format(self, request))
        self.requests.append((request))


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
        self.target = self.last_value

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
        
        target = PWMRequest.get_max_target(self.requests)
        if target is not None:
            self.log_warning('{} could not return to original control ({}), setting it to {}'.format(self, self.__pwm_mode_str(self.original_enable), str(target)))
            if self.__write(self.device_path, self.name, target, ignore_exceptions):
                self.__discard_requests(warn_dropped=False)
                return True
            
        target = self.__get_max()
        self.log_error('{} could not set that either, but try with max value anyway ({})'.format(self, target))
        if not self.__write(self.device_path, self.name, target, ignore_exceptions):
            self.log_error('All attempts failed... hope everything works out for you :-)')

        # Clear requests - just in case we somehow bugged into starting up again
        self.__discard_requests(warn_dropped=False)
        return False


    def __get_max(self):
        '''
        Get the configured maximum value, this should only be used as a
        fail-safe in case the program fails in some way and we should err
        on the side of not cooking things.
        '''
        return max([fan.pwm_max for fan in self.fans], 
                   default=self.PWM_MAX)


    def load_configuration(self):
        super().load_configuration()
        if not os.path.isfile(self.enable_path):
            raise ConfigurationError('{}.{} not found'.format(self, 'enable_path'), self.enable_path)
        self.log_verbose('{}.{} input OK'.format(self, 'enable_path', self.device_path))