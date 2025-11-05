#!/usr/bin/python3

import sys
import argparse
import os
from lib import Settings, PACKAGE, PACKAGE_NAME
from lib.logger import *


class PWMImport(LoggerMixin):
    def __init__(self, settings, logger):
        self.settings = settings
        self.logger = logger


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
        self.settings.save()


    def __import_setting(self, key, value):
        self.settings.set('Settings', key, value)
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
            if not self.settings.have_section(section):
                self.settings.set(section, 'enabled', Settings.DEFAULT_ENABLED)
                self.settings.set(section, 'device', section)
                self.settings.set(section, 'sensor', '')
                self.settings.set(section, 'sensor_min', Settings.DEFAULT_SENSOR_MIN)
                self.settings.set(section, 'sensor_max', Settings.DEFAULT_SENSOR_MAX)
                self.settings.set(section, 'pwm_input', '')
                self.settings.set(section, 'pwm_min', Settings.DEFAULT_PWM_MIN)
                self.settings.set(section, 'pwm_max', Settings.DEFAULT_PWM_MAX)
                self.settings.set(section, 'pwm_start', Settings.DEFAULT_PWM_START)
                self.settings.set(section, 'pwm_stop', Settings.DEFAULT_PWM_STOP)

            self.settings.set(section, key, value)
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


def is_ini(config_path):
    '''
    Configuration might not exist yet, so we only test extension.
    '''
    if not config_path.lower().endswith('.ini'):
        raise argparse.ArgumentError("Unknown extension specified (" + config_path + ")")
    return config_path


def is_config(config_path):
    '''
    Check that the specified configuration file exists
    '''
    if not os.path.isfile(config_path):
        raise argparse.ArgumentError("No suitable file specified (" + config_path + ")")
    return config_path


def main():
    parser = argparse.ArgumentParser()
    parser.description = '''
    Python fancontrol, spinning fans in the 21st century. Specifically
    intended for importing configuration generated by original package.
    '''
    parser.add_argument('-c', '--config-path', type=is_ini, default='fancontrol.ini', help='Specify configuration')
    parser.add_argument('-i', '--import-path', type=is_config, default="/etc/fancontrol", help='Specify configuration')
    parser.add_argument('-v', '--version', action='version', version=PACKAGE, help="Show version information")
    parser.add_argument('--replace', action='store_true', help="Replaces configuration")
    args = parser.parse_args()

    logger = ConsoleLogger(PACKAGE_NAME)

    if os.path.isfile(args.config_path) and not args.replace:
        logger.log(utils.to_keypair_str('Configuration path already exists', args.config_path), Logger.ERROR)
        sys.exit(1) 

    config_tmp = args.config_path + '.tmp'
    if (os.path.isfile(config_tmp)):
        logger.log(utils.to_keypair_str('Removing temporary configuration', config_tmp), Logger.WARNING)
        os.remove(config_tmp)

    settings = Settings(config_tmp, logger)
    importer = PWMImport(settings, logger)
    importer.import_configuration(args.import_path)

    os.rename(config_tmp, args.config_path)
    
if __name__ == "__main__":
    main()
