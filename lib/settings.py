import os, string
from configparser import ConfigParser
from .logger import Logger, LoggerMixin
from .ansi import ANSIFormatter
from .exceptions import ConfigurationError, ControlRuntimeError


class Settings(LoggerMixin):
    SETTINGS = 'Settings'
    SPECIAL_SECTIONS = [ SETTINGS ]
    DEFAULT_ALLOWED_CHARS = string.ascii_letters + string.digits + '_-#.'

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


    def __init__(self, config_path, logger, reconfigure_logger=True, allowed_chars=DEFAULT_ALLOWED_CHARS, auto_create=True):
        '''
        Creates an instance with the configured config_path, by default we will
        create the file if it currently does not exist.
        '''
        self.config_path = config_path
        self.set_logger(logger)
        self.reconfigure_logger = reconfigure_logger
        self.allowed_chars = allowed_chars
        self.config = ConfigParser()
        self.changed = False
        self.create_or_read(auto_create)


    def __getattr__(self, name):
        match name:
            case 'delay':
                return self.config.getint('Settings', name)
            case 'error_on_empty':
                return self.config.getboolean('Settings', name)
        return self.get('Settings', name)


    def create_or_read(self, auto_create=True):
        if os.path.isfile(self.config_path):
            self.config.read(self.config_path)
        self.__restore_key('Settings','log_level', Logger.to_filter_level(Settings.DEFAULT_LOG_LEVEL))
        self.__restore_key('Settings','log_using', Settings.DEFAULT_LOGGER)
        self.__restore_key('Settings','log_formatter', Settings.DEFAULT_LOG_FORMATTER)
        self.__restore_key('Settings','delay', str(Settings.DEFAULT_DELAY))
        self.__restore_key('Settings','error_on_empty', Settings.DEFAULT_ERROR_ON_EMPTY)

        if auto_create and self.changed:
            self.save()


    def save(self):
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)
        self.changed = False


    def sections(self, filter_special=True, only_enabled=True):
        '''
        Retrieves a list of sections found in the configuration, with some
        of them reserved for special use-cases such as 'Settings'.
        '''
        sections = self.config.sections()
        sections = filter(lambda section: self.__include_section(section, filter_special=filter_special, only_enabled=only_enabled), sections)
        sections = list(sections)
        sections.sort()
        return sections


    def __include_section(self, section, filter_special=True, only_enabled=True):
        if filter_special and self.is_special(section):
            return False
        if only_enabled:
            return self.is_enabled(section)
        return True


    def get(self, section, key, fallback = None):
        return self.config.get(section, key, fallback=fallback)


    def getint(self, section, key):
        return self.config.getint(section, key)


    def set(self, section, key, value):
        value = str(value)
        if not self.have_section(section):
            self.check_allowed_chars(section)
            self.create_section(section)
            self.changed = True
        if not self.have_key(section, key):
            self.check_allowed_chars(key)
            self.changed = True
        else:
            if self.get(section, key) != value:
                self.changed = True
        self.config.set(section, key, value)


    def have_section(self, section):
        return section in self.config.sections()
    

    def create_section(self, section):
        if self.have_section(section):
            return
        self.config[section] = {}
        self.set(section, 'enabled', Settings.DEFAULT_ENABLED)
        self.set(section, 'sensor', '')
        self.set(section, 'sensor_min', Settings.DEFAULT_SENSOR_MIN)
        self.set(section, 'sensor_max', Settings.DEFAULT_SENSOR_MAX)
        self.set(section, 'device', '')
        self.set(section, 'pwm_min', Settings.DEFAULT_PWM_MIN)
        self.set(section, 'pwm_max', Settings.DEFAULT_PWM_MAX)
        self.set(section, 'pwm_start', Settings.DEFAULT_PWM_START)
        self.set(section, 'pwm_stop', Settings.DEFAULT_PWM_STOP)
        self.set(section, 'pwm_input', '')


    def remove_section(self, section):
        if not self.have_section(section):
            return
        self.config.remove_section(section)


    def have_key(self, section, key):
        if not self.have_section(section):
            return False
        return key in self.config[section]


    def is_special(self, section):
        return section in self.SPECIAL_SECTIONS


    def is_enabled(self, section, default_value = False):
        key = 'enabled'
        if not self.have_key(section, key):
            return default_value
        return self.config.getboolean(section, key)


    def rename_section(self, section, new_name):
        if not new_name:
            raise ControlRuntimeError('new_name must be set')
        if self.is_special(section):
            raise ControlRuntimeError("{} is a special section".format(section))
        if self.is_special(new_name):
            raise ControlRuntimeError("{} is a special section".format(new_name))
        if not self.have_section(section):
            raise ControlRuntimeError("{} does not exist".format(section))
        if self.have_section(new_name):
            raise ControlRuntimeError("{} already exists".format(new_name))
        
        self.config.add_section(new_name)
        for (key, value) in self.config.items(section):
            self.config.set(new_name, key, value)
        self.config.remove_section(section)
        return True
        

    def set_enabled(self, section, value):
        value = 'yes' if value else 'no'
        self.set(section, 'enabled', value)


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
                    if not self.reconfigure_logger: return
                    if value not in Logger.OUTPUTS:
                        raise ConfigurationError('log_using not recognized (current: {} valid: {})'.format(value, '|'.join(Logger.OUTPUTS)))

                case ['Settings', 'log_formatter']:
                    if not self.reconfigure_logger: return
                    if value not in ANSIFormatter.ALLOWED:
                        raise ConfigurationError('log_formatter not recognized (current: {} valid: {})'.format(value, '|'.join(ANSIFormatter.ALLOWED)))

                case ['Settings', 'log_level']:
                    if not self.reconfigure_logger: return
                    try:
                        value = Logger.to_filter_value(value)
                    except ValueError as e:
                        raise ConfigurationError('log_level not recognized (current: {} valid: <number>|{})'.format(value, '|'.join(Logger.LEVELS)))

                    if value != default:
                        self.configure_logger(value)


    def check_allowed_chars(self, key_string):
        '''
        Check if the supplied key_string will be considered valid by this
        class, commonly used to validate values entered by the user.
        '''
        if not key_string:
            raise ControlRuntimeError("Supplied string was empty")
        for char in key_string:
            if char not in self.allowed_chars:
                raise ControlRuntimeError("Character '{}' not in allowed_chars()".format(char, self.allowed_chars))
        return True
    

    def strip_illegal_chars(self, key_string):
        '''
        Supplied with a key taken from some other resource, we should strip
        away all characters that isn't listed in allowed_chars. Note that the
        result might still not be considered valid by the class, in particular
        if the result has a length of 0.
        '''
        result = []
        for char in key_string:
            if char in self.allowed_chars:
                result.append(char)
        return ''.join(result)