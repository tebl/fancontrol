from ..logger import Logger, InteractiveLogger, PromptBuilder, ConfirmPromptBuilder
from ..exceptions import SensorException, ControlRuntimeError
from ..control import PWMSensor
from .. import utils
from .context import InteractiveContext


class ControlFanContext(InteractiveContext):
    def __init__(self, *args, fan):
        super().__init__(*args)
        self.fan = fan
        self.original_enable = None
        self.original_value = None
        self.managing = False


    def interact(self, auto_select=None):
        if not self.__confirm_warning(auto_select) == self:
            return self.parent

        try:
            self.__save_state()

            while True:
                self.summary()

                input = self.console.prompt_choices(self.__get_prompt_builder(), prompt=self.get_prompt(), auto_select=auto_select)
                result, key = self.__match_actions(input)
            
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


    def __save_state(self):
        self.original_enable = self.__read_enable()
        self.managing = (self.original_enable == PWMSensor.PWM_ENABLE_MANUAL)
        self.original_value = self.__read_value()


    def __read_enable(self):
        return self.fan.device.read_enable()


    def __write_enable(self, value, ignore_exceptions=False):
        return self.__write_to(self.fan.device.enable_path, value, ignore_exceptions=ignore_exceptions)


    def __read_value(self):
        return self.fan.device.read_int(self.fan.device.device_path)


    def __write_value(self, value, ignore_exceptions=False):
        return self.__write_to(self.fan.device.device_path, value, ignore_exceptions=ignore_exceptions)


    def __write_to(self, path, value, ignore_exceptions=False):
        try:
            return self.fan.device.write(path, value)
        except (SensorException, ControlRuntimeError) as e:
            if not ignore_exceptions:
                raise
            self.message('... ignoring exception ({})'.format(e), styling=Logger.WARNING)


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


    KEY_SET_FULL = 'f'
    KEY_SET_ZERO = '0'
    KEY_SET_MANAGED = 'm'
    KEY_SET_CHIPSET = 'c'
    KEY_SET_REFRESH = 'r'
    KEY_SET_VALUE = 'v'


    def __get_prompt_builder(self):
        builder = PromptBuilder(self.console)
        builder.set(self.KEY_SET_MANAGED, self.to_sentence(self.SET, utils.Acronym(self.fan.device.format_enable(PWMSensor.PWM_ENABLE_MANUAL))))
        builder.set(self.KEY_SET_CHIPSET, self.to_sentence(self.SET, utils.Acronym(self.fan.device.format_enable(PWMSensor.PWM_ENABLE_AUTO))))
        builder.set(self.KEY_SET_FULL, 'Set to full')
        builder.set(self.KEY_SET_ZERO, 'Set to zero')
        builder.set(self.KEY_SET_REFRESH, 'Refresh')
        builder.set(self.KEY_SET_VALUE, 'Set value')        
        builder.add_back()
        return builder
    

    def __match_actions(self, input):
        match input:
            case None | 'x':
                return (self.parent, input)
            case self.KEY_SET_CHIPSET:
                return (self.__handle_set_enable(PWMSensor.PWM_ENABLE_AUTO, end='\n\n'), input)
            case self.KEY_SET_MANAGED:
                return (self.__handle_set_enable(PWMSensor.PWM_ENABLE_MANUAL, end='\n\n'), input)
            case self.KEY_SET_ZERO:
                return (self.__handle_set_specific(self.fan.PWM_MIN), input)
            case self.KEY_SET_FULL:
                return (self.__handle_set_specific(self.fan.PWM_MAX), input)
            case self.KEY_SET_VALUE:
                return (self.__handle_set_value(), input)
        return (self, None)


    def __handle_set_enable(self, value, end='\n'):
        self.__write_enable(value, ignore_exceptions=False)
        self.message('PWM enable set to {}'.format(self.fan.device.format_enable(value)), end=end)
        self.managing = (value == PWMSensor.PWM_ENABLE_MANUAL)
        return self
    

    def __handle_set_specific(self, value):
        if not self.__ensure_managed():
            return self
        self.__write_value(value)
        self.message('PWM value set to {}'.format(value), end='\n\n')
        return self


    def __ensure_managed(self):
        if self.managing:
            return True

        warning = (
            'WARNING! In order to perform this action, the fan needs to set'
            'to {}.'
        ).format(self.fan.device.format_enable(PWMSensor.PWM_ENABLE_MANUAL))

        self.message()
        self.message(warning, Logger.WARNING, end='\n\n')
        self.message('Do you want to do this now?', InteractiveLogger.DIRECT_HIGHLIGHT)
        if self.console.prompt_choices(ConfirmPromptBuilder(self.console), prompt=self.CONFIRM) == 'y':
            self.__handle_set_enable(PWMSensor.PWM_ENABLE_MANUAL)
            return True
        self.message()
        return False


    def __handle_set_value(self):
        if not self.__ensure_managed():
            return self
        self.message()
        self.message('Set PWM value:', styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        input = self.console.prompt_input('Enter value', allow_blank=True, validation_func=self.validate_pwm)
        if input:
            return self.__handle_set_specific(input)
        return self


    def __confirm_warning(self, auto_select=None):
        warning = (
            'WARNING! This interface allows the control over fans directly, '
            'meaning that you can potentially shut off something that keeps '
            'your hardware from destroying itself. The author does not take '
            'any responsibility for YOUR actions while using this software. '
            'Please confirm that you understand.'
        )
        self.message(warning, Logger.WARNING, end='\n\n')

        if self.console.prompt_choices(ConfirmPromptBuilder(self.console), prompt=self.CONFIRM, auto_select=auto_select) == 'y':
            self.message()
            return self
        self.message()
        return self.parent