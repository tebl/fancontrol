import traceback
from ..logger import PromptBuilder, Logger
from ..exceptions import ConfigurationError
from .context import InteractiveContext
from .logging import LoggingContext
from .main_loaded import LoadedContext
from .hwmon import HWMONContext


class MainContext(InteractiveContext):
    def __init__(self, *args):
        super().__init__(*args)


    def interact(self):
        builder = PromptBuilder(self.console)
        builder.set('c', 'Load configuration', highlight=True)
        builder.set('h', 'Set hwmon', highlight=True)
        builder.set('l', 'Set logging', highlight=True)
        builder.add_exit()

        self.message('Actions available:')
        input = self.console.prompt_choices(builder)
        match input:
            case None | 'x':
                return self.confirm_exit()
            case 'c':
                if self.__attempt_load():
                    return LoadedContext(self.fan_config, parent=None)
            case 'h':
                return HWMONContext(self.fan_config, self)
            case 'l':
                return LoggingContext(self.fan_config, self)
        return self


    def __attempt_load(self):
        try:
            self.fan_config.settings.create_or_read()
            self.configuration_loaded = self.fan_config.load_configuration()
            if self.configuration_loaded:
                self.message('Configuration loaded.', end='\n\n')
            return True
        except ConfigurationError as e:
            error_str = traceback.format_exc()
            self.error('Configuration error: ')
            self.error(str(e))
            self.message(error_str, styling=Logger.DEBUG)
        return False