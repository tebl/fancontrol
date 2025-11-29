import time, itertools
from ..logger import Logger, InteractiveLogger, PromptBuilder, ConfirmPromptBuilder
from ..exceptions import SensorException, ControlRuntimeError, SchedulerLimitExceeded
from ..control import PWMSensor
from ..scheduler import MicroScheduler
from ..pwm_iterator import PWMIterator
from .. import utils
from .context import InteractiveContext


class ControlFanContext(InteractiveContext):
    KEY_SET_FULL = 'f'
    KEY_SET_ZERO = '0'
    KEY_SET_MANAGED = 'm'
    KEY_SET_CHIPSET = 'c'
    KEY_SET_REFRESH = 'r'
    KEY_SET_VALUE = 'v'
    KEY_SET_TEST = 't'
    KEY_SET_KEEP = 'k'
    KEY_SET_SIMULATE = 's'


    def __init__(self, *args, fan):
        super().__init__(*args)
        self.fan = fan
        self.original_enable = None
        self.original_value = None
        self.managing = False


    def interact(self, auto_select=None):
        if not self.__confirm_usage(auto_select):
            return self.parent

        msg = (
            'Notice: This interface works with a combination of values, both '
            'from the program itself and the underlying driver. This will '
            'give the appearance of values not updating directly after '
            'issuing commands.'
        )
        self.message(msg, end='\n\n')

        try:
            self.__save_state()

            while True:
                self.summary()

                input = self.console.prompt_choices(self.__get_prompt_builder(), prompt=self.get_prompt(), auto_select=auto_select)
                result, key = self.__match_actions(input, auto_select)
            
                if result == self:
                    continue
                return result
        except (SensorException, ControlRuntimeError) as e:
            self.print_error(e, title='Runtime error')
        finally:
            self.__restore_state()
        return self.parent


    def get_prompt(self):
        terms = [ self.fan.get_title() ]
        if self.managing:
            terms.append(self.fan.device.format_enable(PWMSensor.PWM_ENABLE_MANUAL))
        else:
            terms.append(self.fan.device.format_enable(PWMSensor.PWM_ENABLE_AUTO))
        return ' '.join(terms)


    def summary(self, items=None, sep=': ', prefix=InteractiveContext.SUBKEY_INDENT):
        # This is needed as changing items to a default value of [] would cause
        # it to be reused across all function calls. Apparently Python does that.
        if items is None:
            items = []
        
        self.add_summary_value(items, self.NAME, self.fan.get_title())
        self.add_summary_value(items, self.DEVICE, self.fan.device, format_func=self.format_resource, validation_func=self.validate_exists)
        self.add_summary_value(items, self.SUBKEY_CHILD + self.MINIMUM, self.fan.pwm_min, format_func=utils.format_pwm, validation_func=self.validate_exists)
        self.add_summary_value(items, self.SUBKEY_CHILD + self.MAXIMUM, self.fan.pwm_max, format_func=utils.format_pwm, validation_func=self.validate_exists)
        self.add_summary_value(items, self.SUBKEY_CHILD + self.START, self.fan.pwm_start, format_func=utils.format_pwm, validation_func=self.validate_exists)
        self.add_summary_value(items, self.SUBKEY_CHILD + self.STOP, self.fan.pwm_stop, format_func=utils.format_pwm, validation_func=self.validate_exists)
        self.add_summary_value(items, self.SENSOR, self.fan.sensor, format_func=self.format_resource, validation_func=self.validate_exists)
        self.add_summary_value(items, self.SUBKEY_CHILD + self.MINIMUM, self.fan.sensor_min, format_func=utils.format_celsius, validation_func=self.validate_exists)
        self.add_summary_value(items, self.SUBKEY_CHILD + self.MAXIMUM, self.fan.sensor_max, format_func=utils.format_celsius, validation_func=self.validate_exists)
        self.add_summary_value(items, self.PWM_INPUT, self.fan.pwm_input, format_func=self.format_resource, validation_func=self.validate_exists)
        return super().summary(items, sep, prefix)


    def __get_prompt_builder(self):
        builder = PromptBuilder(self.console)
        builder.set(self.KEY_SET_MANAGED, self.to_sentence(self.SET, utils.Acronym(self.fan.device.format_enable(PWMSensor.PWM_ENABLE_MANUAL))))
        builder.set(self.KEY_SET_CHIPSET, self.to_sentence(self.SET, utils.Acronym(self.fan.device.format_enable(PWMSensor.PWM_ENABLE_AUTO))))
        builder.set(self.KEY_SET_FULL, 'Set to full')
        builder.set(self.KEY_SET_ZERO, 'Set to zero')
        builder.set(self.KEY_SET_REFRESH, 'Refresh')
        builder.set(self.KEY_SET_VALUE, 'Set value')        
        builder.set(self.KEY_SET_TEST, 'Test fan limits')
        builder.set(self.KEY_SET_KEEP, 'Keep current values')
        builder.set(self.KEY_SET_SIMULATE, 'Simulate')
        builder.add_back()
        return builder
    

    def __match_actions(self, input, auto_select=None):
        match input:
            case None | 'x':
                return (self.parent, input)
            case self.KEY_SET_CHIPSET:
                self.__handle_set_enable(PWMSensor.PWM_ENABLE_AUTO, end='\n\n')
            case self.KEY_SET_MANAGED:
                self.__handle_set_enable(PWMSensor.PWM_ENABLE_MANUAL, end='\n\n')
            case self.KEY_SET_ZERO:
                self.__handle_set_specific(self.fan.PWM_MIN)
            case self.KEY_SET_FULL:
                self.__handle_set_specific(self.fan.PWM_MAX)
            case self.KEY_SET_VALUE:
                self.__handle_set_value()
            case self.KEY_SET_TEST:
                self.__handle_test(auto_select=auto_select)
            case self.KEY_SET_KEEP:
                self.message('Current driver settings will be kept on exit.', end='\n\n')
                self.__save_state()
            case self.KEY_SET_REFRESH:
                self.message()
            case self.KEY_SET_SIMULATE:
                self.__handle_simulate()
        return (self, input)


    def __handle_set_enable(self, value, end='\n'):
        self.__write_enable(value, ignore_exceptions=False)
        self.message('PWM enable set to {}'.format(self.fan.device.format_enable(value)), end=end)
        self.managing = (value == PWMSensor.PWM_ENABLE_MANUAL)
        return True
    

    def __handle_set_specific(self, value):
        if not self.__ensure_managed():
            return False
        self.__write_value(value)
        self.message('PWM value set to {}'.format(value), end='\n\n')
        return True


    def __handle_set_value(self):
        if not self.__ensure_managed():
            return False
        self.message()
        self.message('Set PWM value:', styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        input = self.console.prompt_input('Enter value', allow_blank=True, validation_func=self.validate_pwm)
        if input:
            return self.__handle_set_specific(input)
        return True


    def __confirm_usage(self, auto_select=None):
        warning = (
            'WARNING! This interface allows the control over fans directly. '
            'This means that you can potentially shut off something that '
            'keeps your hardware from destroying itself. The author does not'
            'take any responsibility for YOUR actions while using this '
            'software.'
        )
        return self.confirm_warning(warning, auto_select=auto_select)

    
    def __handle_simulate(self, temp_from=0, temp_to=100):
        '''
        Simulate requests from the fan with temperatures in the specified
        range (inclusive).
        '''
        self.message()
        items = []

        TemperatureSpan.reset()
        for temperature in range(temp_from, temp_to+1, 5):
            TemperatureSpan.add(temperature, self.fan.simulate(temperature, 100).target_value)
        for result in TemperatureSpan.get():
            self.add_summary_value(items, result.get_description(), result.get_value(), validation_func=self.validate_exists)
        return super().summary(items, title='Simulation results')


    def __handle_test(self, auto_select=None, value_offset=20):
        '''
        Perform fan behavior testing, used to test how a fan responds to 
        various PWM-values.
        '''
        self.message()
        warning = (
            'WARNING! This function needs to take control over the fan by '
            'setting the mode to {}. We will then go through a series of '
            'operations in order to determine the physical behavior of it, '
            'quite possibly leaving you with insufficient cooling. Do NOT '
            'continue unless you know what this means for your system.'
        ).format(self.fan.device.format_enable(PWMSensor.PWM_ENABLE_MANUAL))
        if not self.confirm_warning(warning, auto_select=auto_select):
            return False
        try:
            local_enable = self.__read_enable()
            local_value = self.__read_value()

            device_min, device_max, device_start, device_stop = self.__perform_testing(self.fan.PWM_MIN, self.fan.PWM_MAX)
            device_start = self.__offset_value(device_start, value_offset, self.fan.PWM_MIN, self.fan.PWM_MAX)
            device_stop = self.__offset_value(device_stop, value_offset, self.fan.PWM_MIN, self.fan.PWM_MAX)
            if self.confirm_dialog('Keep fan running?', include_cancel=False, auto_select=auto_select):
                device_min = device_stop
            self.__test_summary(device_min, device_max, device_start, device_stop)

            if self.confirm_dialog('Write to configuration?', include_cancel=False, auto_select=auto_select):
                self.__write_configuration(device_min, device_max, device_start, device_stop)
            return True
        except TestAbortedException as e:
            self.error('Tests aborted: {}'.format(e.message), end='\n\n')
        finally:
            self.__write_value(local_value)
            self.__write_enable(local_enable)
        return False


    def __test_summary(self, device_min, device_max, device_start, device_stop):
        items = []
        self.add_summary_value(items, self.SUBKEY_CHILD + self.DEVICE_MIN, device_min, format_func=utils.format_pwm, validation_func=self.validate_exists)
        self.add_summary_value(items, self.SUBKEY_CHILD + self.DEVICE_MAX, device_max, format_func=utils.format_pwm, validation_func=self.validate_exists)
        self.add_summary_value(items, self.SUBKEY_CHILD + self.DEVICE_START, device_start, format_func=utils.format_pwm, validation_func=self.validate_exists)
        self.add_summary_value(items, self.SUBKEY_CHILD + self.DEVICE_STOP, device_stop, format_func=utils.format_pwm, validation_func=self.validate_exists)
        return super().summary(items, title='Test summary')


    def __write_configuration(self, device_min, device_max, device_start, device_stop):
        self.fan.pwm_min = device_min
        self.fan.pwm_max = device_max
        self.fan.pwm_start = device_start
        self.fan.pwm_stop = device_stop

        self.fan_config.settings.set(self.fan.name, 'pwm_min', device_min)
        self.fan_config.settings.set(self.fan.name, 'pwm_max', device_max)
        self.fan_config.settings.set(self.fan.name, 'pwm_start', device_start)
        self.fan_config.settings.set(self.fan.name, 'pwm_stop', device_stop)
        self.fan_config.settings.save()


    def __perform_testing(self, device_min, device_max, step_size=10):
        device_start = None
        device_stop = None

        with TestContextManager(self, 'Testing ' + self.fan.get_title(), inline=False) as parent_context:
            self.__write_enable(PWMSensor.PWM_ENABLE_MANUAL)

            with TestContextManager(self, 'Stopping fan', parent_context=parent_context) as test_context:
                self.__write_value(self.fan.PWM_MIN)
                try:
                    self.__wait_period(limit=20, check_completed_func=self.__check_stopped)
                except SchedulerLimitExceeded:
                    raise TestAbortedException('fan never stopped - maybe {} doesn\'t actually control {}?'.format(self.fan.device.get_title(), self.fan.pwm_input.get_title()))

            with TestContextManager(self, 'Setting fan to MAX', status_ok='done', parent_context=parent_context) as test_context:
                self.__write_value(self.fan.PWM_MAX)

            with TestContextManager(self, 'Waiting 10 seconds', status_ok='done', parent_context=parent_context) as test_context:
                self.__wait_period(limit=10)

            with TestContextManager(self, 'Verifying that it started', parent_context=parent_context) as test_context:
                try:
                    self.__wait_period(limit=10, check_completed_func=self.__check_started, notify_status=test_context, status_format_func=utils.format_rpm)
                except SchedulerLimitExceeded:
                    raise TestAbortedException('fan never stopped - maybe {} doesn\'t actually control {}?'.format(self.fan.device.get_title(), self.fan.pwm_input.get_title()))

            with TestContextManager(self, 'Find ' + self.DEVICE_STOP, parent_context=parent_context) as test_context:
                for value in PWMIterator(self.fan.PWM_MIN, self.fan.PWM_MAX, -step_size):
                    test_context.debug(value)
                    self.__write_value(value)
                    try:
                        if self.__wait_period(step_delay=0.5, limit=4, check_completed_func=self.__check_stopped):
                            device_stop = value
                            test_context.set_status(device_stop)
                            break
                    except SchedulerLimitExceeded:
                        pass
                if device_stop is None:
                    raise TestAbortedException('fan never stopped - maybe {} doesn\'t actually control {}?'.format(self.fan.device.get_title(), self.fan.pwm_input.get_title()))

            with TestContextManager(self, 'Stopping fan', parent_context=parent_context) as test_context:
                self.__write_value(self.fan.PWM_MIN)
                try:
                    self.__wait_period(limit=20, check_completed_func=self.__check_stopped)
                except SchedulerLimitExceeded:
                    raise TestAbortedException('fan never stopped - maybe {} doesn\'t actually control {}?'.format(self.fan.device.get_title(), self.fan.pwm_input.get_title()))

            with TestContextManager(self, 'Find ' + self.DEVICE_START, parent_context=parent_context) as test_context:
                start_at = self.fan.PWM_MIN if device_stop is None else device_stop
                for value in PWMIterator(start_at, self.fan.PWM_MAX, step_size):
                    test_context.debug(value)
                    self.__write_value(value)
                    try:
                        if self.__wait_period(step_delay=0.2, limit=5, check_completed_func=self.__check_started):
                            device_start = value
                            test_context.set_status(device_start)
                            break
                    except SchedulerLimitExceeded:
                        pass
                if device_start is None:
                    raise TestAbortedException('fan never started - maybe {} doesn\'t actually control {}?'.format(self.fan.device.get_title(), self.fan.pwm_input.get_title()))
        self.message()
        return device_min, device_max, device_start, device_stop


    def __wait_period(self, step_delay=1, limit=None, check_completed_func=None, notify_status=None, status_format_func=None):
        '''
        '''
        scheduler = MicroScheduler(self.fan_config.logger, step_delay=step_delay, limit=limit)
        scheduler.set_next()
        while self.fan_config.running:
            if scheduler.was_passed():
                try:
                    scheduler.set_next()
                except SchedulerLimitExceeded:
                    # If we have a check function, but reached the limit then
                    # we've we've had a timeout error. Without one set we
                    # instead assume that a timeout is what we wanted in the
                    # first place.
                    if check_completed_func is not None:
                        raise
                    return False
            else:
                time.sleep(.3)
            if check_completed_func is not None:
                result = check_completed_func()
                if result:
                    if notify_status is not None:
                        notify_msg = result
                        if status_format_func:
                            notify_msg = status_format_func(result)
                        notify_status.set_status(notify_msg)
                    return True
        return False


    def __check_stopped(self):
        '''
        Verify that the fan has come to a full stop
        '''
        return self.__read_rpm() == 0


    def __check_started(self):
        return self.__read_rpm()


    def __offset_value(self, value, offset, min, max):
        value = value + offset
        if value < min:
            return min
        if value > max:
            return max
        return value


    def __ensure_managed(self):
        '''
        Some functions can only be performed while a fan is directly
        controlled, but we need to ask for a confirmation before doing so.
        '''
        if self.managing:
            return True

        warning = (
            'WARNING! In order to perform this action, control over the fan '
            'needs to set to {}.'
        ).format(self.fan.device.format_enable(PWMSensor.PWM_ENABLE_MANUAL))

        if self.confirm_warning(warning):
            self.__handle_set_enable(PWMSensor.PWM_ENABLE_MANUAL)
            return True
        return False


    def __save_state(self):
        self.original_enable = self.__read_enable()
        self.managing = (self.original_enable == PWMSensor.PWM_ENABLE_MANUAL)
        self.original_value = self.__read_value()


    def __read_enable(self):
        return self.fan.device.read_enable()


    def __write_enable(self, value, ignore_exceptions=False):
        return self.fan.device.write_enable(value, ignore_exceptions)


    def __read_value(self):
        return self.fan.device.read_value()


    def __read_rpm(self):
        return self.fan.pwm_input.read_value()


    def __write_value(self, value, ignore_exceptions=False):
        return self.fan.device.write_value(value, ignore_exceptions)


    def __restore_state(self):
        changes = False
        if self.original_value is not None:
            if not self.__read_value() == self.original_value:
                changes = True
                self.__write_value(self.original_value, ignore_exceptions=True)
                self.message('Restored original value: {}'.format(self.original_value))

        if self.original_enable is not None:
            if not self.__read_enable() == self.original_enable:
                changes = True
                self.__write_enable(self.original_enable, ignore_exceptions=True)
                self.message('Restored original enable: {}'.format(self.fan.device.format_enable(self.original_enable)))
        if changes:
            self.message()


class TestContextManager:
    def __init__(self, context, message, styling=InteractiveLogger.DIRECT_REGULAR, status_ok='OK', status_fail='FAILED', inline=True, parent_context=None):
        self.context = context
        self.message = message
        self.styling = styling
        self.status_ok = status_ok
        self.status_fail = status_fail
        self.inline = inline
        self.parent = parent_context
        self.indent_number = 0
        if parent_context:
            self.indent_number = parent_context.next_indent()
        self.status = None


    def set_status(self, status):
        self.status = str(status)


    def get_result(self, result):
        if self.status:
            result = '{} ({})'.format(result, self.status)
        return result


    def get_indent(self):
        if self.indent_number == 0:
            return ''
        if self.indent_number == 1:
            return self.context.SUBKEY_CHILD
        return self.context.SUBKEY_INDENT*(self.indent_number - 1) + self.context.SUBKEY_CHILD


    def next_indent(self):
        return self.indent_number + 1


    def debug(self, message):
        message = str(message)
        if self.inline:
            self.context.message(message, styling=Logger.DEBUG, end=' ')
            return
        message = '{}{}'.format(self.get_indent(), message)
        self.context.message(message, styling=Logger.DEBUG)


    def __enter__(self):
        end = '' if self.inline else '\n'
        self.context.message('{}{}... '.format(self.get_indent(), self.message), styling=self.styling, end=end)
        return self


    def __exit__(self, exc_type, exc_value, traceback):
        prefix = '' if self.inline else self.get_indent() + '... '
        if exc_type is None:
            self.context.message('{}{}'.format(prefix, self.get_result(self.status_ok)), styling=self.styling)
        else:
            self.context.message('{}{}'.format(prefix, self.get_result(self.status_fail)), styling=self.styling)
        return False


class TestAbortedException(ControlRuntimeError):
    '''
    Used during fan behavior testing.
    '''


class TemperatureSpan:
    instances = []


    def __init__(self, start_at, value):
        self.start_at = start_at
        self.stop_at = start_at
        self.value = value


    def get_description(self):
        result = 'At {}'.format(utils.format_celsius(self.start_at))
        if self.stop_at != self.start_at:
            result += ' until {}'.format(utils.format_celsius(self.stop_at))
        return result


    def get_value(self):
        return utils.format_pwm(self.value)


    @classmethod
    def add(cls, temperature, value, fill_gaps=True):
        if not cls.instances:
            cls.instances.append(cls(start_at=temperature, value=value))
        last = cls.instances[-1]
        if last.value == value:
            last.stop_at = temperature
        else:
            if fill_gaps and last.stop_at < (temperature - 1):
                last.stop_at = temperature - 1
            cls.instances.append(cls(start_at=temperature, value=value))


    @classmethod
    def get(cls):
        return cls.instances


    @classmethod
    def reset(cls):
        cls.instances.clear()