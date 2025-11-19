import os
from ..logger import Logger, InteractiveLogger, PromptBuilder, ConfirmPromptBuilder, PromptValidationException
from ..exceptions import ControlRuntimeError
from ..hwmon_info import HwmonInfo
from .. import utils
from .context import InteractiveContext


class SectionContext(InteractiveContext):
    KEY_DEVICE = 'd'
    KEY_DEVICE_MIN = '1'
    KEY_DEVICE_MAX = '2'
    KEY_DEVICE_START = '3'
    KEY_DEVICE_STOP = '4'
    KEY_ENABLE = 'e'
    KEY_NAME = 'n'
    KEY_SENSE = 'p'
    KEY_DELETE = 'r'
    KEY_SENSOR = 's'
    KEY_SENSOR_MIN = '5'
    KEY_SENSOR_MAX = '6'


    def __init__(self, *args, section):
        super().__init__(*args)
        self.section = section


    def interact(self):
        self.summary()

        input = self.console.prompt_choices(self.__get_prompt_builder(), prompt=self.section)
        match input:
            case None | 'x':
                return self.parent
            case self.KEY_DEVICE_MIN:
                return self.__set_value('Device Min', 'pwm_min', validation_func=self.__validate_pwm_min)
            case self.KEY_DEVICE_MAX:
                return self.__set_value('Device Max', 'pwm_max', validation_func=self.__validate_pwm_max)
            case self.KEY_DEVICE_START:
                return self.__set_value('Device Min', 'pwm_start', validation_func=self.validate_pwm)
            case self.KEY_DEVICE_STOP:
                return self.__set_value('Device Max', 'pwm_stop', validation_func=self.validate_pwm)
            case self.KEY_SENSOR_MIN:
                return self.__set_value('Sensor Min', 'sensor_min', validation_func=self.validate_temp)
            case self.KEY_SENSOR_MAX:
                return self.__set_value('Sensor Max', 'sensor_max', validation_func=self.validate_temp)
            case self.KEY_DEVICE:
                return self.__handle_device()
            case self.KEY_ENABLE:
                return self.__handle_enable()
            case self.KEY_NAME:
                return self.__handle_rename()
            case self.KEY_SENSE:
                return self.__handle_pwm_input()
            case self.KEY_DELETE:
                return self.__handle_remove()
            case self.KEY_SENSOR:
                return self.__handle_sensor()
        return self


    def summary(self, items=None, sep=': ', prefix=InteractiveContext.SUBKEY_INDENT):
        # This is needed as changing items to a default value of [] would cause
        # it to be reused across all function calls. Apparently Python does that.
        if items is None:
            items = []

        self.add_summary_value(items, 'Name', self.section)
        self.add_summary_config(items, 'Device', 'device')
        self.__add_status(items)
        self.add_summary_config(items, self.SUBKEY_CHILD + "Minimum", 'pwm_min', format_func=utils.format_pwm, validation_func=self.__validate_pwm_min, format_dict={ 'key': self.KEY_DEVICE_MIN })
        self.add_summary_config(items, self.SUBKEY_CHILD + "Maximum", 'pwm_max', format_func=utils.format_pwm, validation_func=self.__validate_pwm_max, format_dict={ 'key': self.KEY_DEVICE_MAX })
        self.add_summary_config(items, self.SUBKEY_CHILD + "Start", 'pwm_start', format_func=utils.format_pwm, validation_func=self.validate_pwm, format_dict={ 'key': self.KEY_DEVICE_START })
        self.add_summary_config(items, self.SUBKEY_CHILD + "Stop", 'pwm_stop', format_func=utils.format_pwm, validation_func=self.__validate_pwm_stop, format_dict={ 'key': self.KEY_DEVICE_STOP })
        self.add_summary_config(items, 'Sensor', 'sensor')
        self.add_summary_config(items, self.SUBKEY_CHILD + "Minimum", 'sensor_min', format_func=utils.format_celsius, validation_func=self.__validate_sensor_min, format_dict={ 'key': self.KEY_SENSOR_MIN })
        self.add_summary_config(items, self.SUBKEY_CHILD + "Maximum", 'sensor_max', format_func=utils.format_celsius, validation_func=self.validate_temp, format_dict={ 'key': self.KEY_SENSOR_MAX })
        self.add_summary_config(items, 'PWM Input', 'pwm_input')
        return super().summary(items, sep, prefix)


    def __validate_pwm_min(self, value, extended=False):
        value = self.validate_pwm(value, extended)
        if extended and value >= self.fan_config.settings.getint(self.section, 'pwm_max'):
            raise PromptValidationException('must be less than Device Max')
        return value


    def __validate_pwm_max(self, value, extended=False):
        value = self.validate_pwm(value, extended)
        if extended and value < self.fan_config.settings.getint(self.section, 'pwm_min'):
            raise PromptValidationException('must be more than Device Min')
        return value
    

    def __validate_pwm_stop(self, value, extended=False):
        value = self.validate_pwm(value, extended)
        if extended and value >= self.fan_config.settings.getint(self.section, 'pwm_max'):
            raise PromptValidationException('must be less than Device Max')
        if extended and value < self.fan_config.settings.getint(self.section, 'pwm_min'):
            raise PromptValidationException('must be larger than Device Min')
        return value
    

    def __validate_sensor_min(self, value, extended=False):
        value = self.validate_temp(value)
        if extended and value >= self.fan_config.settings.getint(self.section, 'sensor_max'):
            raise PromptValidationException('must be less than Sensor Max')
        return value


    def __add_status(self, summary):
        enabled = self.fan_config.settings.is_enabled(self.section)
        if enabled:
            summary.append([self.SUBKEY_CHILD + "Status", 'Enabled'])
        else:
            summary.append([self.SUBKEY_CHILD + "Status", 'Disabled', {'styling': Logger.WARNING}])


    def __set_value(self, name, key, validation_func):
        self.message()
        self.message('Set {}:'.format(name), styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        input = self.console.prompt_input('Enter value', allow_blank=True, validation_func=validation_func)
        if input:
            try:
                self.fan_config.settings.set(self.section, key, input)
                self.fan_config.settings.save()
                self.message('Configuration updated.', end='\n\n')

            except ControlRuntimeError as e:
                self.error('Renaming failed with error ({})'.format(e.message), end='\n\n')
        return self
    

    def __get_prompt_builder(self):
        builder = PromptBuilder(self.console)
        builder.set(self.KEY_DELETE, 'Remove')
        builder.set(self.KEY_SENSOR, 'Set sensor')
        builder.set(self.KEY_SENSE, 'Set PWM Input')
        builder.set(self.KEY_DEVICE, 'Set device')
        builder.set(self.KEY_NAME, 'Change name')
        builder.set(self.KEY_DEVICE_MIN, 'Device Min')
        builder.set(self.KEY_DEVICE_MAX, 'Device Max')
        builder.set(self.KEY_DEVICE_START, 'Device Start')
        builder.set(self.KEY_DEVICE_STOP, 'Device Stop')
        builder.set(self.KEY_SENSOR_MIN, 'Sensor Min')
        builder.set(self.KEY_SENSOR_MAX, 'Sensor Max')
        self.__add_toggle_enabled(builder)
        builder.add_back()
        return builder


    def __add_toggle_enabled(self, builder):
        enabled = self.fan_config.settings.is_enabled(self.section)
        builder.set(self.KEY_ENABLE, 'Disable' if enabled else 'Enable')


    def __handle_enable(self):
        self.fan_config.settings.set_enabled(self.section, not self.fan_config.settings.is_enabled(self.section))
        self.fan_config.settings.save()
        self.message('Configuration updated.', end='\n\n')
        return self


    def __handle_rename(self):
        self.message()
        self.message('Renaming {}:'.format(str(self.section)), styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        input = self.console.prompt_input('Name', allow_blank=True, validation_func=self.__validate_name)
        if input:
            try:
                if self.fan_config.settings.rename_section(self.section, input):
                    self.section = input
                    self.message('Configuration updated.', end='\n\n')
            except ControlRuntimeError as e:
                self.error('Renaming failed with error ({})'.format(e.message), end='\n\n')
        return self
    

    def __validate_name(self, name):
        return self.fan_config.settings.check_allowed_chars(name)


    def __handle_remove(self):
        self.message()
        self.message('Removing {}:'.format(str(self.section)), styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        if self.console.prompt_choices(ConfirmPromptBuilder(self.console), prompt='Confirm') == 'y':
            self.fan_config.settings.remove_section(self.section)
            self.message('Section removed.', end='\n\n')
            return self.parent
        return self


    def __handle_device(self):
        return self.__select_resource(prompt='Select device', read_attribute='devices', write_attribute='device', validation_func=self.__hwmon_has_devices)


    def __handle_pwm_input(self):
        return self.__select_resource(prompt='Select PWM Input', read_attribute='pwm_inputs', write_attribute='pwm_input', validation_func=self.__hwmon_has_pwm_inputs)


    def __handle_sensor(self):
        return self.__select_resource(prompt='Select sensor', read_attribute='sensors', write_attribute='sensor', validation_func=self.__hwmon_has_sensors)


    def __select_resource(self, prompt, read_attribute, write_attribute, validation_func):
        '''
        Lists hwmon-instances, allowing you to choose one of them as well as
        subsequently prompting you to choose one of the resources provided by
        it.
        '''
        current_value = self.fan_config.settings.get(self.section, write_attribute)
        current_hwmon = HwmonInfo.get_hwmon_from_value(current_value, self.fan_config.settings.dev_base)
        current_entry = HwmonInfo.get_entry_from_value(current_value, self.fan_config.settings.dev_base)

        self.message()
        hwmon_info = self.__select_hwmon(current_hwmon, validation_func=validation_func)
        if not hwmon_info:
            return self

        self.message()
        hwmon_entry = self.hwmon_select_entry(
            hwmon_entries = getattr(hwmon_info, read_attribute),
            current_hwmon = current_hwmon,
            current_entry = current_entry,
            prompt = prompt
        )

        if not hwmon_entry:
            return self

        self.fan_config.settings.set(self.section, write_attribute, hwmon_entry.get_input(dev_base=self.fan_config.settings.dev_base))
        self.fan_config.settings.save()
        self.message('Configuration updated.', end='\n\n')

        return self


    def __select_hwmon(self, current, validation_func):
        '''
        Loads information from hwmon, gives a formatted listing before allowing
        you to choose one of them. Validation function can be passed as
        reference in order to qualify hwmon-candidates.
        '''
        hwmon_list = self.hwmon_load(validation_func)
        self.hwmon_list(hwmon_list, current)
        return self.hwmon_select(hwmon_list, current)


    def __hwmon_has_devices(self, hwmon_entry):
        return hwmon_entry.devices
   

    def __hwmon_has_pwm_inputs(self, hwmon_entry):
        return hwmon_entry.pwm_inputs


    def __hwmon_has_sensors(self, hwmon_entry):
        return hwmon_entry.sensors