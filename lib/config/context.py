from ..logger import LoggerMixin, Logger, InteractiveLogger, ConfirmPromptBuilder


class InteractiveContext(LoggerMixin):
    SUBKEY_INDENT = '  '

    def __init__(self, fan_config, parent):
        self.fan_config = fan_config
        self.parent = parent
        self.console = self.fan_config.console


    # def __getattribute__(self, name):
    #     match name:
    #         case 'console':
    #             return self.fan_config.console
    #     return super().__getattribute__(name)

    
    def interact(self):
        '''
        Nothing here, but that's only to be expected from a base class. The
        script will interact with contexts through a version of this method,
        returning a different context, or itself, that should become the new
        context from this point on.
        '''
        return self.parent
    

    def message(self, message='', styling=InteractiveLogger.DIRECT_REGULAR, end='\n'):
        self.console.log_direct(message, styling=styling, end=end)


    def error(self, message, styling=Logger.ERROR, end='\n'):
        self.message(message, styling=styling, end=end)


    def summarise(self, list, sep=': ', prefix=''):
        '''
        Used near the start of a context interaction to summarise common values
        used in this section. List should have the structure of (key, value)
        and the key is used so that we align all values on the screen.
        '''
        if not list:
            return
        self.message('Summary:', styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        key_pad = len(max([key for key, value in list], key=len)) + len(sep)
        for key, value in list:
            self.message(prefix + self.format_key_value(key, value, key_pad=key_pad, sep=sep))


    def confirm_exit(self):
        if self.console.prompt_choices(ConfirmPromptBuilder(self.console), prompt='Confirm exit') == 'y':
            return self.parent
        return self


    def format_key_value(self, key, value, key_pad=16, sep=' '):
        if key_pad:
            return (key + sep).ljust(key_pad) + str(value)
        return (key + sep) + str(value)


    def format_pwm(self, value):
        return '({}/255)'.format(str(value).rjust(3))
    

    def format_temp(self, value):
        return str(value) + "°C"


    def toggle_from_list(self, list, current, default):
        '''
        Used when stepping through possible values, one after another. Makes
        a copy so that we don't destroy anything valuable, but it will wrap
        around as needed.
        '''
        methods = list.copy()
        try:
            methods.append(methods[0])
            index = methods.index(current)
            return methods[index + 1]
        except ValueError:
            return default


    def expain_setting(self, name, value, description):
        '''
        Used to standardise how a setting explanation is printed. Nothing too
        exciting going on except for the fact that we're assuming that this is
        mainly for debugging.
        '''
        self.message('{} set to {}'.format(name, value))
        self.message(description.format(name, value), styling=Logger.DEBUG, end='\n\n')


    def __str__(self):
        suffix = 'Context'
        name = self.__class__.__name__
        if name.endswith(suffix):
            name = name[:-len(suffix)]
        return name