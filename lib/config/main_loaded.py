from ..logger import LoggerMixin, Logger, InteractiveLogger, PromptBuilder, ConfirmPromptBuilder
from ..exceptions import ConfigurationError
from .context import InteractiveContext
from .fans_loaded import FansLoadedContext
from .section import SectionContext


class LoadedContext(InteractiveContext):
    '''
    Used after the configuration has been successfully loaded by fan_config,
    and the assumption is that the same would be possible for fancontrol as 
    well. Offers ability to configure fan configurations.

    Note: As we don't really have a method for unloading a configuration, we
          don't know how to get back to the main menu. So if we hit x here we
          exit completely.
    '''
    def interact(self):
        self.summary([
            ['Delay', 'Controller updates every {} seconds'.format(self.fan_config.delay)],
            ['Device', self.fan_config.get_path()],
            [self.SUBKEY_CHILD + 'Path checked', self.fan_config.dev_path],
            [self.SUBKEY_CHILD + 'Driver checked', self.fan_config.dev_name]
        ])

        self.__load_sections()
        self.__list_sections()

        input = self.console.prompt_choices(self.__get_prompt_builder())
        match input:
            case None | 'x':
                return self.confirm_exit()
            case 'c':
                if self.__attempt_load_fans():
                    return FansLoadedContext(self.fan_config, parent=None)
            case _:
                section = self.prompt_values[input]
                self.message('Fan definition {} selected.'.format(section), end='\n\n')
                return SectionContext(self.fan_config, self, section=section)
        return self


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
