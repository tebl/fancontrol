from ..logger import LoggerMixin, Logger, InteractiveLogger


class InteractiveContext(LoggerMixin):
    SUBKEY_INDENT = '  '

    def __init__(self, fan_config, parent):
        self.fan_config = fan_config
        self.parent = parent
        self.console = self.fan_config.console


    def __getattribute__(self, name):
        match name:
            case 'console':
                return self.fan_config.console
        return super().__getattribute__(name)

    
    def interact(self):
        return self.parent
    

    def message(self, message='', styling=InteractiveLogger.DIRECT_REGULAR, end='\n'):
        self.console.log_direct(message, styling=styling, end=end)


    def error(self, message, styling=Logger.ERROR, end='\n'):
        self.message(message, styling=styling, end=end)


    def summarise(self, list, sep=': ', prefix=''):
        if not list:
            return
        self.message('Summary:', styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        key_pad = len(max([key for key, value in list], key=len)) + len(sep)
        for key, value in list:
            self.message(prefix + self.format_key_value(key, value, key_pad=key_pad, sep=sep))


    def format_key_value(self, key, value, key_pad=16, sep=' '):
        if key_pad:
            return (key + sep).ljust(key_pad) + str(value)
        return (key + sep) + str(value)


    def format_pwm(self, value):
        return '({}/255)'.format(str(value).rjust(3))
    

    def format_temp(self, value):
        return str(value) + "°C"