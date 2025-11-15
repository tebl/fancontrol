from ..logger import LoggerMixin, Logger, InteractiveLogger, PromptBuilder, ConfirmPromptBuilder
from ..ansi import ANSIFormatter
from .context import InteractiveContext
from .fans import FanContext


class LoadedContext(InteractiveContext):
    '''
    Used after the configuration has been successfully loaded by fan_config,
    and the assumption is that the same would be possible for fancontrol as 
    well. Offers that ability to configure fan configurations.

    Note: As we don't really have a method for unloading a configuration, we
          don't know how to get back to the main menu. So if we hit x here we
          exit completely.
    '''
    def interact(self):
        self.summarise([
            ['Delay', 'Controller updates every {} seconds'.format(self.fan_config.delay)],
            ['Device', self.fan_config.get_path()],
            [self.SUBKEY_CHILD + 'Path checked', self.fan_config.dev_path],
            [self.SUBKEY_CHILD + 'Driver checked', self.fan_config.dev_name]
        ])

        self.__list_fans()

        input = self.console.prompt_choices(self.__get_prompt_builder())
        match input:
            case None | 'x':
                return self.confirm_exit()
            case _:
                fan = self.prompt_values[input]
                self.message('Fan {} selected'.format(fan.get_title()), end='\n\n')
                return FanContext(self.fan_config, self, fan=fan)
        return self


    def __list_fans(self):
        self.message('Listing available definitions:', styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        for fan in self.fan_config.fans:
            self.message(self.SUBKEY_INDENT + fan.get_title(include_summary=True), styling=Logger.DEBUG)
        self.message()


    def __get_prompt_builder(self):
        builder = PromptBuilder(self.console)
        builder.add_exit()
        self.__add_fan_options(builder)
        return builder
    

    def __add_fan_options(self, builder):
        self.prompt_values = {}
        for fan in self.fan_config.fans:
            key = builder.set_next(fan.get_title())
            self.prompt_values[key] = fan
