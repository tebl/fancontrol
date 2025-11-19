from ..logger import LoggerMixin, Logger, InteractiveLogger, PromptBuilder
from ..ansi import ANSIFormatter
from .context import InteractiveContext


class LoggingContext(InteractiveContext):
    LOG_FORMATTING = 'Log formatting'
    LOG_LEVEL = 'Log level'
    LOG_USING = 'Log using'

    def __init__(self, *args):
        super().__init__(*args)


    def interact(self):
        self.summary([
            [self.LOG_USING, self.fan_config.settings.log_using],
            [self.SUBKEY_CHILD + self.LOG_FORMATTING, self.fan_config.settings.log_formatter],
            [self.SUBKEY_CHILD + self.LOG_LEVEL, self.fan_config.settings.log_level],
        ])

        input = self.console.prompt_choices(self.__get_prompt_builder(), prompt=self)
        match input:
            case None | 'x':
                return self.parent
            case 'e':
                self.__explain_using(self.LOG_USING, self.fan_config.settings.log_using)
                self.__explain_formatter(self.LOG_FORMATTING, self.fan_config.settings.log_formatter)
                self.__explain_level(self.LOG_LEVEL, self.fan_config.settings.log_level)
            case 'l':
                value = self.__toggle_level(self.fan_config.settings.log_level)
                self.fan_config.settings.set('Settings', 'log_level', value)
                self.fan_config.settings.save()
                self.__explain_level(self.LOG_LEVEL, value)
            case 'f':
                value = self.__toggle_formatter(self.fan_config.settings.log_formatter)
                self.fan_config.settings.set('Settings', 'log_formatter', value)
                self.fan_config.settings.save()
                self.__explain_formatter(self.LOG_FORMATTING, value)
            case 'u':
                value = self.__toggle_using(self.fan_config.settings.log_using)
                self.fan_config.settings.set('Settings', 'log_using', value)
                self.fan_config.settings.save()
                self.__explain_using(self.LOG_USING, value)
        return self


    def __toggle_level(self, current):
        return self.toggle_from_list(Logger.LEVELS, current, Logger.STR_INFO)


    def __toggle_formatter(self, current):
        return self.toggle_from_list(ANSIFormatter.ALLOWED, current, ANSIFormatter.BASIC)


    def __toggle_using(self, current):
        return self.toggle_from_list(Logger.OUTPUTS, current, Logger.STR_INFO)


    def __get_prompt_builder(self):
        builder = PromptBuilder(self.console)
        builder.add_back()
        builder.set('e', 'Explain')
        builder.set('l', 'Toggle level')
        builder.set('u', 'Toggle using')
        builder.set('f', 'Toggle formatting')
        return builder
    

    def __explain_level(self, name, value):
        description = ('When running the software will only log messages with '
                       'a level at or above {1}')
        self.expain_setting(name, value, description)


    def __explain_formatter(self, name, value):
        match value:
            case ANSIFormatter.MONOCHROME:
                description = (
                    'Log entries will be logged without ANSI-formatting, '
                    'resulting in plain text')
            case ANSIFormatter.BASIC:
                description = (
                    'Log entries will be formatted using basic terminal '
                    'colours, ie. 16-colours')
            case _:
                description = (
                    'Log entries will be formatted using up to 256 colours, '
                    'something that may not work on every terminal though they '
                    'look nicer on my screen')
        self.expain_setting(name, value, description)
    

    def __explain_using(self, name, value):
        match value:
            case Logger.CONSOLE:
                description = (
                    'Log entries are printed with tags showing log level')
            case Logger.LOG_FILE:
                description = (
                    'Log entries will be printed similar to CONSOLE, but now '
                    'with a timestamp - making it a suitable option for '
                    'redirecting script output to a file')
            case Logger.JOURNAL:
                description = 'Logs are written using systemd-journal'
            case _:
                description = ''
        self.expain_setting(name, value, description)