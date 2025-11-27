from ..logger import PromptBuilder
from ..exceptions import ConfigurationError
from .. import PACKAGE
from .context import InteractiveContext
from .logging import LoggingContext
from .main_loaded import MainLoadedContext
from .hwmon import HWMONContext


class MainContext(InteractiveContext):
    def interact(self, auto_select=None):
        self.summary()

        self.message(InteractiveContext.ACTIONS + ':')
        input = self.console.prompt_choices(self.__get_prompt_builder(), prompt=self, auto_select=auto_select)
        match input:
            case None | 'x':
                return self.confirm_exit()
            case 'c':
                if self.__attempt_load():
                    return MainLoadedContext(self.fan_config, self)
            case 'h':
                return HWMONContext(self.fan_config, self)
            case 'l':
                return LoggingContext(self.fan_config, self)
        return self


    def summary(self, items=None, sep=': ', prefix=InteractiveContext.SUBKEY_INDENT):
        # This is needed as changing items to a default value of [] would cause
        # it to be reused across all function calls. Apparently Python does that.
        if items is None:
            items = []

        self.add_summary_config(items, 'Delay', 'delay', format_func=MainLoadedContext.format_delay, validation_func=self.validate_string)
        self.add_summary_config(items, 'Device', 'dev_base', validation_func=self.validate_string)
        self.add_summary_config(items, self.SUBKEY_CHILD + 'Path checked', 'dev_path', validation_func=self.validate_string)
        self.add_summary_config(items, self.SUBKEY_CHILD + 'Driver checked', 'dev_name', validation_func=self.validate_string)
        self.add_summary_logging(items)
        return super().summary(items, sep, prefix)


    def add_summary_logging(self, items):
        self.add_summary_config(items, LoggingContext.LOG_USING, 'log_using')
        self.add_summary_config(items, self.SUBKEY_CHILD + LoggingContext.LOG_FORMATTING, 'log_formatter', validation_func=self.validate_string)
        self.add_summary_config(items, self.SUBKEY_CHILD + LoggingContext.LOG_LEVEL, 'log_level', validation_func=self.validate_string)


    def __get_prompt_builder(self):
        builder = PromptBuilder(self.console)
        builder.set('c', 'Load configuration', highlight=True)
        builder.set('h', 'Set hwmon', highlight=True)
        builder.set('l', 'Set logging', highlight=True)
        builder.add_exit()
        return builder


    def __attempt_load(self):
        try:
            self.fan_config.settings.create_or_read()
            if not self.fan_config.load_configuration():
                return False
            self.message('Configuration loaded.', end='\n')
            if not self.fan_config.load_dependencies():
                return False
            self.message('Dependencies loaded.', end='\n\n')
            return True
        except ConfigurationError as e:
            self.print_error(e, title='Configuration error')
        return False