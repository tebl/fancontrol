from ..logger import Logger, InteractiveLogger, PromptBuilder, ConfirmPromptBuilder
from ..exceptions import ControlRuntimeError
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
            case 'e':
                return self.__handle_enable()
            case 'n':
                return self.__handle_rename()
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
        builder.set('s', 'Sensor')
        builder.set('i', 'PWM Input')
        builder.set('d', 'Device')
        builder.set('n', 'Set name')


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