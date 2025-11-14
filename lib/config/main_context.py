import traceback
from ..logger import PromptBuilder
from ..exceptions import ConfigurationError
from .context import InteractiveContext
from .fan_context import FanContext


class MainContext(InteractiveContext):
    def __init__(self, *args):
        super().__init__(*args)
        self.configuration_loaded = False


    def interact(self):
        if not self.configuration_loaded:
            return self.__prompt_empty()
        return self.__prompt_loaded()


    def __prompt_loaded(self):
        self.summarise([
            ['Delay', 'Controller updates every {} seconds'.format(self.fan_config.delay)],
            ['Device', self.fan_config.get_path()],
            [self.SUBKEY_INDENT + 'Path checked', self.fan_config.dev_path],
            [self.SUBKEY_INDENT + 'Driver checked', self.fan_config.dev_name]
        ])

        self.message()
        self.message('Listing available definitions:')
        input = self.console.prompt_choices(self.__get_prompt_builder())
        match input:
            case None | 'x':
                return self.parent
            case _:
                fan = self.prompt_values[input]
                self.message('Fan {} selected'.format(fan.get_title()), end='\n\n')
                return FanContext(self.fan_config, self, fan=fan)


    def __prompt_empty(self):
        self.message('Actions available:')
        input = self.console.prompt_choices(self.__get_prompt_builder())
        match input:
            case None | 'x':
                return self.parent
            case 'l':
                self.__attempt_load()
        return self


    def __attempt_load(self):
        try:
            self.configuration_loaded = self.fan_config.load_configuration()
            if self.configuration_loaded:
                self.message('Configuration loaded.', end='\n\n')
        except ConfigurationError as e:
            error_str = traceback.format_exc()
            self.error('Configuration error on load_configuration()' + error_str)


    def __get_prompt_builder(self):
        builder = PromptBuilder(self.console)

        if self.configuration_loaded:
            self.__add_fan_options(builder)
        else:
            builder.set('l', 'Load configuration', True)

        builder.add_exit()
        return builder
    

    def __add_fan_options(self, builder):
        self.prompt_values = {}
        for fan in self.fan_config.fans:
            key = builder.set_next(fan.get_title())
            self.prompt_values[key] = fan
