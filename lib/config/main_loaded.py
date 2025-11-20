import uuid
from ..logger import Logger, InteractiveLogger, PromptBuilder, ConfirmPromptBuilder
from ..exceptions import ConfigurationError
from .context import InteractiveContext
from .main_complete import MainCompleteContext
from .section import SectionContext
from .logging import LoggingContext


class MainLoadedContext(InteractiveContext):
    '''
    Used after the configuration has been successfully loaded by fan_config,
    and the assumption is that the same would be possible for fancontrol as 
    well. Offers ability to configure fan configurations.
    '''


    def interact(self, auto_select=None):
        self.summary()

        self.__load_sections()
        self.__list_sections()

        input = self.console.prompt_choices(self.__get_prompt_builder(), prompt=self, auto_select=auto_select)
        match input:
            case None | 'x':
                return self.parent
            case 'c':
                if self.__attempt_load_fans():
                    return MainCompleteContext(self.fan_config, parent=None)
            case 'n':
                return SectionContext(self.fan_config, self, section=str(uuid.uuid4())).create()
            case _:
                section = self.prompt_values[input]
                self.message('Fan definition {} selected.'.format(section), end='\n\n')
                return SectionContext(self.fan_config, self, section=section)
        return self


    def summary(self, items=None, sep=': ', prefix=InteractiveContext.SUBKEY_INDENT):
        # This is needed as changing items to a default value of [] would cause
        # it to be reused across all function calls. Apparently Python does that.
        if items is None:
            items = []

        self.add_summary_value(items, 'Delay', self.fan_config.delay, format_func=self.format_delay)
        self.add_summary_value(items, 'Device', self.fan_config.dev_base)
        self.add_summary_value(items, self.SUBKEY_CHILD + 'Path checked', self.fan_config.dev_path)
        self.add_summary_value(items, self.SUBKEY_CHILD + 'Driver checked', self.fan_config.dev_name)
        self.add_summary_config(items, LoggingContext.LOG_USING, 'log_using')
        self.add_summary_config(items, self.SUBKEY_CHILD + LoggingContext.LOG_FORMATTING, 'log_formatter', validation_func=self.validate_string)
        self.add_summary_config(items, self.SUBKEY_CHILD + LoggingContext.LOG_LEVEL, 'log_level', validation_func=self.validate_string)
        return super().summary(items, sep, prefix)


    def __load_sections(self):
        self.sections = []
        for section in self.fan_config.settings.sections(only_enabled=False):
            self.sections.append(section)


    def __list_sections(self):
        self.message('Listing available definitions:', styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        for section in self.sections:
            self.__output_section(section)
        self.message()


    def __output_section(self, section):
        description = section
        terms = []
        styling = Logger.DEBUG
        if not self.fan_config.settings.is_enabled(section):
            styling = Logger.WARNING
            terms.append('disabled')
        if terms:
            description = '{} ({})'.format(description, ', '.join(terms))
        self.message(self.SUBKEY_INDENT + description, styling=styling)


    def __get_prompt_builder(self):
        builder = PromptBuilder(self.console)
        self.prompt_values = {}
        builder.set('c', 'Load fan configuration', highlight=True, reorder=True)
        builder.set('n', 'New fan configuration', highlight=True, reorder=True)
        builder.add_exit(reorder=True)
        for section in self.sections:
            key = builder.set_next(section)
            self.prompt_values[key] = section
        return builder
    

    def __attempt_load_fans(self):
        try:
            self.fan_config.settings.create_or_read()
            self.configuration_loaded = self.fan_config.load_fans()
            if self.configuration_loaded:
                self.message('Fan configuration loaded.', end='\n\n')
            return True
        except ConfigurationError as e:
            self.error('Configuration error: ')
            self.error(self.SUBKEY_INDENT + str(e), end='\n\n')
        return False


    @staticmethod
    def format_delay(value):
        return 'Controller updates every {} seconds'.format(value)