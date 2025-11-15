from ..logger import LoggerMixin, Logger, InteractiveLogger, PromptBuilder
from .context import InteractiveContext


class SectionContext(InteractiveContext):
    def __init__(self, *args, section):
        super().__init__(*args)
        self.section = section


    def interact(self):
        enabled = self.fan_config.settings.is_enabled(self.section)
        self.summarise([
            ['Name', self.section],
            [
                'Enabled', 
                'yes' if enabled else 'no',
                Logger.DEBUG if enabled else Logger.WARNING
            ]
            # [self.SUBKEY_INDENT + 'Minimum', self.format_pwm(self.fan.pwm_min)],
            # [self.SUBKEY_INDENT + 'Maximum', self.format_pwm(self.fan.pwm_max)],
            # [self.SUBKEY_INDENT + 'Start', self.format_pwm(self.fan.pwm_start)],
            # [self.SUBKEY_INDENT + 'Stop', self.format_pwm(self.fan.pwm_stop)],
            # ['Based on', self.fan.sensor],
            # [self.SUBKEY_INDENT + 'Minimum', self.format_temp(self.fan.sensor_min)],
            # [self.SUBKEY_INDENT + 'Maximum', self.format_temp(self.fan.sensor_max)]
        ])

        input = self.console.prompt_choices(self.__get_prompt_builder(), prompt=self.section)
        match input:
            case None | 'x':
                return self.parent
            case _:
                self.message('You entered ' + input)
                return self
        return self


    def __get_prompt_builder(self):
        builder = PromptBuilder(self.console)
        # self.prompt_values = {}
        # for fan in self.fan_config.fans:
        #     key = builder.set_next(fan.get_title())
        #     self.prompt_values[key] = fan
        builder.add_back()
        return builder
