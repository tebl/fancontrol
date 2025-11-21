from ..logger import LoggerMixin, Logger, InteractiveLogger, PromptBuilder
from .. import utils
from .context import InteractiveContext
from .section import SectionContext


class ControlFanContext(InteractiveContext):
    def __init__(self, *args, fan):
        super().__init__(*args)
        self.fan = fan


    def interact(self, auto_select=None):
        self.summary()

        input = self.console.prompt_choices(self.__get_prompt_builder(), prompt=self.fan.get_title(), auto_select=auto_select)
        match input:
            case None | 'x':
                return self.parent
            case _:
                self.message('You entered ' + input)
                return self
        return self


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
        # self.prompt_values = {}
        # for fan in self.fan_config.fans:
        #     key = builder.set_next(fan.get_title())
        #     self.prompt_values[key] = fan
        builder.add_back()
        return builder


    # def validate_input(self, value):
    #     return value == 'end'
