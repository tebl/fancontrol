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

        # self.summary([
        #     ['Controlled by', self.fan.device],
        #     [self.SUBKEY_INDENT + 'Minimum', utils.format_pwm(self.fan.pwm_min)],
        #     [self.SUBKEY_INDENT + 'Maximum', utils.format_pwm(self.fan.pwm_max)],
        #     [self.SUBKEY_INDENT + 'Start', utils.format_pwm(self.fan.pwm_start)],
        #     [self.SUBKEY_INDENT + 'Stop', utils.format_pwm(self.fan.pwm_stop)],
        #     ['Based on', self.fan.sensor],
        #     [self.SUBKEY_INDENT + 'Minimum', utils.format_celsius(self.fan.sensor_min)],
        #     [self.SUBKEY_INDENT + 'Maximum', utils.format_celsius(self.fan.sensor_max)]
        # ])

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

        self.add_summary_value(items, SectionContext.DEVICE_MIN, 'test')

        return super().summary(items, sep, prefix)


    # def summary(self, items=None, sep=': ', prefix=InteractiveContext.SUBKEY_INDENT):
    #     # This is needed as changing items to a default value of [] would cause
    #     # it to be reused across all function calls. Apparently Python does that.
    #     if items is None:
    #         items = []

    #     self.add_summary_value(items, self.NAME, self.section)
    #     self.add_summary_config(items, self.DEVICE, 'device', validation_func=self.__validate_resource)
    #     self.__add_status(items)
    #     self.add_summary_config(items, self.SUBKEY_CHILD + self.MINIMUM, 'pwm_min', format_func=utils.format_pwm, validation_func=self.__validate_pwm_min, format_dict={ 'key': self.KEY_DEVICE_MIN })
    #     self.add_summary_config(items, self.SUBKEY_CHILD + self.MAXIMUM, 'pwm_max', format_func=utils.format_pwm, validation_func=self.__validate_pwm_max, format_dict={ 'key': self.KEY_DEVICE_MAX })
    #     self.add_summary_config(items, self.SUBKEY_CHILD + self.START, 'pwm_start', format_func=utils.format_pwm, validation_func=self.validate_pwm, format_dict={ 'key': self.KEY_DEVICE_START })
    #     self.add_summary_config(items, self.SUBKEY_CHILD + self.STOP, 'pwm_stop', format_func=utils.format_pwm, validation_func=self.__validate_pwm_stop, format_dict={ 'key': self.KEY_DEVICE_STOP })
    #     self.add_summary_config(items, self.SENSOR, 'sensor', validation_func=self.__validate_resource)
    #     self.add_summary_config(items, self.SUBKEY_CHILD + self.MINIMUM, 'sensor_min', format_func=utils.format_celsius, validation_func=self.__validate_sensor_min, format_dict={ 'key': self.KEY_SENSOR_MIN })
    #     self.add_summary_config(items, self.SUBKEY_CHILD + self.MAXIMUM, 'sensor_max', format_func=utils.format_celsius, validation_func=self.validate_temp, format_dict={ 'key': self.KEY_SENSOR_MAX })
    #     self.add_summary_config(items, self.PWM_INPUT, 'pwm_input', validation_func=self.__validate_resource)
    #     return super().summary(items, sep, prefix)


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
