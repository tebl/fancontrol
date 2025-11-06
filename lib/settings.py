import os
from configparser import ConfigParser
from .logger import Logger, LoggerMixin, ANSIFormatter
from .exceptions import ConfigurationError


class Settings(LoggerMixin):
    DEFAULT_LOG_LEVEL = Logger.INFO
    DEFAULT_LOGGER = Logger.CONSOLE
    DEFAULT_LOG_FORMATTER = ANSIFormatter.BASIC

    DEFAULT_DELAY = 10
    DEFAULT_ERROR_ON_EMPTY = 'yes'

    DEFAULT_ENABLED = 'yes'
    DEFAULT_SENSOR_MIN = 20
    DEFAULT_SENSOR_MAX = 60
    DEFAULT_PWM_MIN = 0
    DEFAULT_PWM_MAX = 255
    DEFAULT_PWM_START = 32
    DEFAULT_PWM_STOP = 40


    def __init__(self, config_path, logger):
        self.set_logger(logger)
        self.config = ConfigParser()
        self.config_path = config_path
        self.changed = False
        self.create_or_read()


    def __getattr__(self, attr):
        match attr:
            case 'delay':
                return self.config.getint('Settings', attr)
            case 'error_on_empty':
                return self.config.getboolean('Settings', attr)

        return self.get('Settings', attr)


    def create_or_read(self):
        if os.path.isfile(self.config_path):
            self.config.read(self.config_path)
        self.__restore_key('Settings','log_level', Logger.to_filter_level(Settings.DEFAULT_LOG_LEVEL))
        self.__restore_key('Settings','log_using', Settings.DEFAULT_LOGGER)
        self.__restore_key('Settings','log_formatter', Settings.DEFAULT_LOG_FORMATTER)
        self.__restore_key('Settings','delay', str(Settings.DEFAULT_DELAY))
        self.__restore_key('Settings','error_on_empty', Settings.DEFAULT_ERROR_ON_EMPTY)

        if self.changed:
            self.save()


    def save(self):
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)
        self.changed = False


    def sections(self, filter_special=True):
        sections = self.config.sections()
        sections = filter(lambda section: self.__include_section(section, filter_special), sections)
        return list(sections)


    def __include_section(self, section, filter_special=True):
        if filter_special and section in ['Settings']:
            return False
        return self.is_enabled(section, 'enabled')


    def get(self, section, key, fallback = None):
        return self.config.get(section, key, fallback=fallback)


    def getint(self, section, key):
        return self.config.getint(section, key)


    def set(self, section, key, value):
        value = str(value)
        if not self.have_section(section):
            self.config[section] = {}
            self.changed = True
        if not self.have_key(section, key):
            self.changed = True
        else:
            if self.get(section, key) != value:
                self.changed = True
        self.config.set(section, key, value)


    def have_section(self, section):
        return section in self.config.sections()


    def have_key(self, section, key):
        if not self.have_section(section):
            return False
        return key in self.config[section]


    def is_enabled(self, section, key, default_value = False):
        if not self.have_key(section, key):
            return default_value
        return self.config.getboolean(section, key)


    def __restore_key(self, section, key, default):
        if section not in self.config.sections():
            self.config[section] = {}
            self.changed = True

        if key not in self.config[section]:
            self.changed = True
            self.config[section][key] = default
        else:
            value = self.get(section, key)
            match [section, key]:
                case ['Settings', 'log_using']:
                    if value not in Logger.OUTPUTS:
                        raise ConfigurationError('log_using not recognized (current: {} valid: {})'.format(value, '|'.join(Logger.OUTPUTS)))

                case ['Settings', 'log_formatter']:
                    if value not in ANSIFormatter.ALLOWED:
                        raise ConfigurationError('log_formatter not recognized (current: {} valid: {})'.format(value, '|'.join(ANSIFormatter.ALLOWED)))

                case ['Settings', 'log_level']:
                    try:
                        value = Logger.to_filter_value(value)
                    except ValueError as e:
                        raise ConfigurationError('log_level not recognized (current: {} valid: <number>|{})'.format(value, '|'.join(Logger.LEVELS)))

                    if value != default:
                        self.configure_logger(value)
