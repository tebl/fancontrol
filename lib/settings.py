import os
from configparser import ConfigParser
from .logger import Logger, LoggerMixin

class Settings(LoggerMixin):
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
        self.__restore_key('Settings','log_level', 'INFO')

        if self.changed:
            self.save()


    def save(self):
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)
        self.changed = False


    def get(self, section, key):
        return self.config[section][key]


    def set(self, section, key, value):
        if section not in self.config.sections():
            self.config[section] = {}
            self.changed = True
        self.config[section][key] = value


    def import_configuration(self, input_path):
        self.log_info("Importing from", input_path)
        self.save()


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
