import os
from ..logger import Logger, InteractiveLogger, PromptBuilder, ConfirmPromptBuilder
from ..exceptions import ControlRuntimeError
from ..control import BaseControl
from ..hwmon_info import HwmonInfo
from .context import InteractiveContext


class SectionContext(InteractiveContext):
    def __init__(self, *args, section):
        super().__init__(*args)
        self.section = section


    def interact(self):
        self.__summarise(self.fan_config.settings)

        input = self.console.prompt_choices(self.__get_prompt_builder(), prompt=self.section)
        match input:
            case None | 'x':
                return self.parent
            case 'd':
                return self.__handle_device()
            case 'e':
                return self.__handle_enable()
            case 'n':
                return self.__handle_rename()
            case 'p':
                return self.__handle_pwm_input()
            case 'r':
                return self.__handle_remove()
        return self


    def __summarise(self, config):
        self.summarise([
            ['Name', self.section],
            self.__summarise_status(),
            ["Device", config.get(self.section, 'device')],
            [self.SUBKEY_CHILD + "Minimum", self.format_pwm(config.getint(self.section, 'pwm_min'))],
            [self.SUBKEY_CHILD + "Maximum", self.format_pwm(config.getint(self.section, 'pwm_max'))],
            [self.SUBKEY_CHILD + "Start", self.format_pwm(config.getint(self.section, 'pwm_start'))],
            [self.SUBKEY_CHILD + "Stop", self.format_pwm(config.getint(self.section, 'pwm_stop'))],
            ["Sensor", config.get(self.section, 'sensor')],
            [self.SUBKEY_CHILD + "Minimum", self.format_temp(config.getint(self.section, 'sensor_min'))],
            [self.SUBKEY_CHILD + "Maximum", self.format_temp(config.getint(self.section, 'sensor_max'))],
            ["PWM Input", config.get(self.section, 'pwm_input')]
        ])
    

    def __summarise_status(self):
        enabled = self.fan_config.settings.is_enabled(self.section)
        if enabled:
            return [self.SUBKEY_CHILD + "Status", 'Enabled']
        return [self.SUBKEY_CHILD + "Status", 'Disabled', Logger.WARNING]


    def __get_prompt_builder(self):
        builder = PromptBuilder(self.console)
        self.__add_toggle_enabled(builder)
        builder.add_back()
        return builder


    def __add_toggle_enabled(self, builder):
        enabled = self.fan_config.settings.is_enabled(self.section)
        builder.set('e', 'Disable' if enabled else 'Enable')
        builder.set('r', 'Remove')
        builder.set('s', 'Set sensor')
        builder.set('p', 'Set PWM Input')
        builder.set('d', 'Set device')
        builder.set('n', 'Change name')


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
        return self.__select_resource(prompt='Select PWM Input', read_attribute='pwm_inputs', write_attribute='pwm_input', validation_func=self.__hwmon_has_devices)


    def __select_resource(self, read_attribute, write_attribute, validation_func, prompt='Select'):
        self.message()
        hwmon_info = self.__select_hwmon(self.fan_config.settings.dev_base, validation_func=validation_func)
        if not hwmon_info:
            return self

        self.message()
        pwm_input = self.hwmon_select_entry(
            hwmon_info,
            getattr(hwmon_info, read_attribute),
            self.fan_config.settings.dev_base,
            self.fan_config.settings.get(self.section, write_attribute),
            prompt=prompt
        )

        if not pwm_input:
            return self

        self.fan_config.settings.set(self.section, write_attribute, pwm_input.input)
        self.fan_config.settings.save()
        self.message('Configuration updated.', end='\n\n')

        return self


    def __hwmon_has_devices(self, hwmon_entry):
        return hwmon_entry.devices


    def __handle_pwm_input(self):
        self.message()
        hwmon_info = self.__select_hwmon(self.fan_config.settings.dev_base, validation_func=self.__hwmon_has_pwm_inputs)
        if not hwmon_info:
            return self

        self.message()
        pwm_input = self.hwmon_select_entry(
            hwmon_info,
            hwmon_info.pwm_inputs,
            self.fan_config.settings.dev_base,
            self.fan_config.settings.get(self.section, 'pwm_input'),
            prompt='Select PWM Input'
        )

        if not pwm_input:
            return self

        self.fan_config.settings.set(self.section, 'pwm_input', pwm_input.input)
        self.fan_config.settings.save()
        self.message('Configuration updated.', end='\n\n')

        return self
    

    def __select_hwmon(self, current, validation_func):
        hwmon_list = self.hwmon_load(validation_func)
        self.hwmon_list(hwmon_list)
        return self.hwmon_select(hwmon_list, current)


    def __hwmon_has_pwm_inputs(self, hwmon_entry):
        return hwmon_entry.pwm_inputs
