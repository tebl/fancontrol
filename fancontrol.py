#!/usr/bin/python3

import sys
import argparse
import os
from lib import Settings, PACKAGE_VERSION
from lib.logger import *
from pprint import pprint


class FanControl(LoggerMixin):
    def __init__(self, settings, logger):
        self.settings = settings
        self.logger = logger
        self.read_configuration()


    def read_configuration(self):
        if self.settings.delay < 1:
            raise ConfigurationError("delay can't be less than 1", self.settings.delay)
        for key in ['log_level', 'dev_base', 'dev_name', 'dev_path']:
            value = self.settings.get('Settings', key)
            if not value:
                raise ConfigurationError(key + " has not been set", value)

        self.load_fans()
        if not self.fans:
            if self.settings.error_on_empty:
                raise ConfigurationError('No enabled fans!')
            self.log_warning('No enabled fans!')


    def load_fans(self):
        self.fans = []
        for name in self.settings.sections():
            fan = Fan(self.settings, self.logger, name)
            self.fans.append(fan)
        return self.fans


    def set_logger(self, logger):
        for fan in self.fans:
            fan.set_logger(logger)
        return super().set_logger(logger)


class Fan(LoggerMixin):
    PWM_MIN = 0
    PWM_MAX = 255

    def __init__(self, settings, logger, name):
        self.settings = settings
        self.logger = logger
        self.name = name
        self.read_configuration()
        self.log_debug('Fan "{}" initialized OK'.format(self))


    def __str__(self):
        return 'Fan "{}"'.format(self.name)


    def read_configuration(self):
        if not self.name:
            raise ConfigurationError('Malformed fan name', self.name)
        if not self.settings.have_section(self.name):
            raise ConfigurationError('Fan configuration not found', self)
        
        self.enabled = self.settings.is_enabled(self.name, 'enabled')
        self.device = self.settings.get(self.name, 'device')

        if not self.device:
            raise ConfigurationError('Setting "device" not set', self)

        self.sensor = self.settings.get(self.name, 'sensor')
        if not self.sensor:
            raise ConfigurationError('Setting "sensor" not set', self)
        
        self.sensor_min = self.settings.getint(self.name, 'sensor_min')
        self.sensor_max = self.settings.getint(self.name, 'sensor_max')
        if self.sensor_min >= self.sensor_max:
            raise ConfigurationError('Setting "sensor_min" ({}) must be lower than "pwm_max" ({})'.format(self.sensor_min, self.sensor_max))

        self.pwm_input = self.settings.get(self.name, 'pwm_input')
        if not self.pwm_input:
            raise ConfigurationError('Setting "pwm_input" not set', self)

        self.pwm_min = self.settings.getint(self.name, 'pwm_min')
        if self.pwm_min < Fan.PWM_MIN:
            raise ConfigurationError('Setting "pwm_min" must be at least {}" ({})'.format(Fan.PWM_MIN, self.pwm_min))

        self.pwm_max = self.settings.getint(self.name, 'pwm_max')
        if self.pwm_max > Fan.PWM_MAX:
            raise ConfigurationError('Setting "pwm_max" can\'t exceed {} ({})'.format(Fan.PWM_MAX, self.pwm_max))

        self.pwm_start = self.settings.getint(self.name, 'pwm_start')
        self.pwm_stop = self.settings.getint(self.name, 'pwm_stop')
        if self.pwm_stop >= self.pwm_max:
            raise ConfigurationError('Setting "pwm_stop" ({}) must be lower than "pwm_max" ({})'.format(self.pwm_stop, self.pwm_max))


class ConfigurationError(Exception):
    def __init__(self, message, details = None):
        if details:
            super().__init__(Logger.to_key_value(message, details))
        else:
            super().__init__(message)


def is_config(config_path):
    '''
    Check that the specified configuration file actually exists and has the
    right extension, but beyond that we're not looking at the contents of it.
    '''
    if not os.path.isfile(config_path):
        raise argparse.ArgumentError(Logger.to_key_value('No suitable file specified', config_path))
    if not config_path.lower().endswith(('.ini')):
        raise argparse.ArgumentError(Logger.to_key_value('Unknown extension specified', config_path))
    return config_path


def perform_verify(run_verify, logger, settings):
    '''
    Loads up the configuration then returns, this hopefully will allow us to
    check if the runtime environment is somewhat sane before doing something
    as insane as for instance stopping the CPU-fan. 
    '''
    if not run_verify:
        return False

    try:
        logger.log(PACKAGE_VERSION)
        FanControl(settings, logger)
        logger.log('OK.')
    except ConfigurationError as e:
        logger.log(str(e), Logger.ERROR)
        sys.exit(1)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.description = 'Python fancontrol, spinning fans in the 21st century'
    parser.add_argument('-c', '--config-path', type=is_config, default='fancontrol.ini', help='Specify configuration')
    parser.add_argument('-v', '--version', action='version', version=PACKAGE_VERSION, help="Show version information")
    parser.add_argument('--verify', action='store_true', help='Fancontrol will load and check configuration before exiting')
    args = parser.parse_args()

    logger = ConsoleLogger()
    settings = Settings(args.config_path, logger)

    # If we're only running a verification of the configuration
    if perform_verify(args.verify, logger, settings):
        sys.exit(0)

    # From this point on the assumption is that we are no longer running
    # interactively. First step is to switch to a more suitable logger.
    logger = LogfileLogger(settings.log_level)
    logger.log('Initialized ' + str(logger), Logger.DEBUG)

    try:
        fancontrol = FanControl(settings, logger)
    except ConfigurationError as e:
        logger.log(str(e), Logger.ERROR)
        sys.exit(1)

if __name__ == "__main__":
    main()
