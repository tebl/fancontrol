import time
from ..logger import Logger, InteractiveLogger, PromptBuilder
from .context import InteractiveContext
from .fan_control import ControlFanContext
from .. import utils


class MainCompleteContext(InteractiveContext):
    def interact(self, auto_select=None):
        self.summary()
        self.__list_fans()

        self.message(InteractiveContext.ACTIONS + ':')
        input = self.console.prompt_choices(self.__get_prompt_builder(), prompt=self, auto_select=auto_select)
        match input:
            case None | 'x':
                return self.parent
            case 'w':
                self.watch_fans(fan_list=self.fan_config.fans)
            case _:
                fan = self.prompt_values[input]
                self.message('Fan {} selected'.format(fan.get_title()), end='\n\n')
                return ControlFanContext(self.fan_config, self, fan=fan)
        return self


    def summary(self, items=None, sep=': ', prefix=InteractiveContext.SUBKEY_INDENT):
        # This is needed as changing items to a default value of [] would cause
        # it to be reused across all function calls. Apparently Python does that.
        if items is None:
            items = []

        self.add_summary_value(items, self.DELAY, self.fan_config.delay, format_func=self.format_delay, validation_func=self.validate_exists)
        self.add_summary_value(items, self.DEVICE, self.fan_config.dev_base.get_title(include_summary=True), validation_func=self.validate_exists)
        self.add_summary_value(items, self.SUBKEY_CHILD + 'Path checked', self.fan_config.dev_path, validation_func=self.validate_exists)
        self.add_summary_value(items, self.SUBKEY_CHILD + 'Driver checked', self.fan_config.dev_name, validation_func=self.validate_exists)
        return super().summary(items, sep, prefix)


    def __get_prompt_builder(self):
        builder = PromptBuilder(self.console)
        self.__add_fan_options(builder)
        builder.add_back()
        builder.set('w', 'Watch sensors')
        return builder


    def __list_fans(self):
        self.message('Listing available definitions:', styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        for fan in self.fan_config.fans:
            self.message(self.SUBKEY_INDENT + fan.get_title(include_summary=True), styling=Logger.DEBUG)
        self.message()


    def __add_fan_options(self, builder):
        self.prompt_values = {}
        for fan in self.fan_config.fans:
            key = builder.set_next(fan.get_title())
            self.prompt_values[key] = fan


    def watch_fans(self, fan_list, sep=': ', prefix=InteractiveContext.SUBKEY_INDENT, update_seconds=1):
        self.message()
        while True:
            try:
                num_lines = 0
                for fan in fan_list:
                    items = []
                    self.add_summary_value(items, self.DEVICE, fan.device, format_func=self.format_resource, validation_func=self.validate_exists)
                    self.add_summary_value(items, self.SENSOR, fan.sensor, format_func=self.format_resource, validation_func=self.validate_exists)
                    self.add_summary_value(items, self.PWM_INPUT, fan.pwm_input, format_func=self.format_resource, validation_func=self.validate_exists)
                    num_lines += super().summary(items, sep, prefix, title=fan.get_title())
                self.message('Updating sensors in {} {}, Ctrl+C to abort.'.format(update_seconds, utils.to_plural('second', count=update_seconds)), InteractiveLogger.DIRECT_PROMPT)
                num_lines += 1
                time.sleep(update_seconds)
                self.console.clear_previous_line(count=num_lines)
            except KeyboardInterrupt:
                return