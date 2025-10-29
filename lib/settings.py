import os
from configparser import ConfigParser
from .logger import Logger, LoggerMixin
from pprint import pprint

class Settings(LoggerMixin):
    DEFAULT_LOG_LEVEL = Logger.INFO
    DEFAULT_DELAY = 10
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
        # if attr == 'generate_hex':
        #     return self.config.getboolean('Settings', attr)
        return self.get('Settings', attr)


    def create_or_read(self):
        if os.path.isfile(self.config_path):
            self.config.read(self.config_path)
        self.__restore_key('Settings','log_level', Logger.to_filter_level(Settings.DEFAULT_LOG_LEVEL))
        self.__restore_key('Settings','delay', str(Settings.DEFAULT_DELAY))

        if self.changed:
            self.save()


    def save(self):
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)
        self.changed = False


    def get(self, section, key):
        return self.config[section][key]


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
        self.config[section][key] = value


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


    def import_configuration(self, input_path):
        self.log_info("Importing from", input_path)
        data = self.__read_configuration(input_path)
        self.__import_setting('delay', data['INTERVAL'])

        dev_base = None
        dev_base = self.__import_key(dev_base, 'dev_name', data['DEVNAME'])
        dev_base = self.__import_key(dev_base, 'dev_path', data['DEVPATH'])

        for (key_from, key_to) in [
            ('FCTEMPS', 'sensor'),
            ('MINTEMP', 'sensor_min'),
            ('MAXTEMP', 'sensor_max'),

            ('FCFANS', 'pwm_input'),
            ('MINPWM', 'pwm_min'),
            ('MAXPWM', 'pwm_max'),
            ('MINSTART', 'pwm_start'),
            ('MINSTOP', 'pwm_stop')
        ]:
            # Process key if it was recovered from the configuration, but
            # silently ignored if not (picked up later in sanity check).
            if key_from in data:
                value = data[key_from]
                self.__import_pwm(dev_base, key_to, value)
        self.save()


    def __import_setting(self, key, value):
        self.set('Settings', key, value)
        self.__log_import(value, key)


    def __log_import(self, value, *args):
        self.log_info('.'.join(args) + '=' + value)


    def __import_key(self, dev_base, key, line):
        next_base, value = self.__get_keypair(line)
        if dev_base == None:
            self.__import_setting('dev_base', next_base)
            dev_base = next_base
        else:
            if dev_base != next_base:
                raise ValueError('Multiple values for "dev_base" encountered')

        self.__import_setting(key, value)
        return dev_base


    def __import_pwm(self, dev_base, key, values):
        if dev_base == None:
            raise ValueError('Value "dev_base" not set')

        for i, (section, value) in enumerate(values.items()):
            section = section.removeprefix(dev_base + os.path.sep)
            value = value.removeprefix(dev_base + os.path.sep)

            # Set pwm_device if this is the first time encountering it,
            # this is the device used. Sections are otherwise just used
            # as display names - we'd be wise to expect users to change
            # them.
            if not self.have_section(section):
                self.set(section, 'enabled', Settings.DEFAULT_ENABLED)
                self.set(section, 'device', section)
                self.set(section, 'sensor', '')
                self.set(section, 'sensor_min', Settings.DEFAULT_SENSOR_MIN)
                self.set(section, 'sensor_max', Settings.DEFAULT_SENSOR_MAX)
                self.set(section, 'pwm_input', '')
                self.set(section, 'pwm_min', Settings.DEFAULT_PWM_MIN)
                self.set(section, 'pwm_max', Settings.DEFAULT_PWM_MAX)
                self.set(section, 'pwm_start', Settings.DEFAULT_PWM_START)
                self.set(section, 'pwm_stop', Settings.DEFAULT_PWM_STOP)

            self.set(section, key, value)
            self.__log_import(value, section, key)


    def __read_configuration(self, input_path):
        data = {}
        with open(input_path) as file:
            for line in file:
                line = self.__strip_comments(line)
                if not line:
                    continue

                try:
                    key, value = self.__parse_line(line)
                    data[key] = value
                except ValueError as e:
                    self.log_warning("Could not parse line: ", line)
        return data


    def __strip_comments(self, line):
        line = line.strip()
        index = line.find('#')
        if index < 0:
            return line
        if index == 0:
            return None
        return line[0:index]


    def __parse_line(self, line):
        key, value = self.__get_keypair(line)

        match key:
            case 'INTERVAL' | 'DEVPATH' | 'DEVNAME':
                return key, value
            case 'FCTEMPS' | 'FCFANS' | 'MINTEMP' | 'MAXTEMP' | 'MINSTART' | 'MINSTOP' | 'MINPWM' | 'MAXPWM':
                values = {}
                for entry in value.split(' '):
                    sub_key, sub_value = self.__get_keypair(entry)
                    values[sub_key] = sub_value
                return key, values
            case _:
                raise ValueError("Unknown key (" + key + ")")


    def __get_keypair(self, line):
        index = line.index('=')
        key = line[0:index].strip()
        value = line[index+1:].strip()
        return key, value


    def __restore_key(self, section, key, default):
        if section not in self.config.sections():
            self.config[section] = {}
            self.changed = True

        if key not in self.config[section]:
            self.changed = True
            self.config[section][key] = default
        else:
            value = self.get(section, key)
            if (value != default):
                match [section, key]:
                    case ['Settings', 'log_level']:
                        self.configure_logger(value)
