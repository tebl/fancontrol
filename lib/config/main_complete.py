from ..logger import Logger, InteractiveLogger, PromptBuilder
from .context import InteractiveContext
from .fan_control import ControlFanContext


class MainCompleteContext(InteractiveContext):
    def interact(self, auto_select=None):
        self.summary()
        self.__list_fans()

        self.message(InteractiveContext.ACTIONS + ':')
        input = self.console.prompt_choices(self.__get_prompt_builder(), prompt=self, auto_select=auto_select)
        match input:
            case None | 'x':
                return self.confirm_exit()
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
        builder.add_exit()
        self.__add_fan_options(builder)
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
