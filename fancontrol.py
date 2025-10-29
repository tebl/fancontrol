#!/usr/bin/python3

import sys
import argparse
import os
from lib import Settings, PACKAGE_VERSION
from lib.logger import *


class FanControl(LoggerMixin):
    def __init__(self, settings, logger):
        self.settings = settings
        self.logger = logger
        self.sanity_check()


    def sanity_check(self):
        if self.settings.delay < 1:
            raise ConfigurationError("delay can't be less than 1", self.settings.delay)
        for key in ['log_level', 'dev_base', 'dev_name', 'dev_path']:
            value = self.settings.get('Settings', key)
            if not value:
                raise ConfigurationError(key + " has not been set", value)


    def reconfigure_logger(self):
        logger = LogfileLogger(self.settings.log_level)
        self.set_logger(logger)
        self.log_info("Log initialized")

    
    def set_logger(self, logger):
        self.settings.set_logger(logger)
        return super().set_logger(logger)


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
    parser.add_argument('--verify', action='store_true', help='Fancontrol will load and check configuration, then exit')
    args = parser.parse_args()

    logger = ConsoleLogger()
    settings = Settings(args.config_path, logger)

    # If we're only running a verification of the configuration
    if perform_verify(args.verify, logger, settings):
        sys.exit(0)

    # From this point on the assumption is that we are no longer
    # running interactively.
    fancontrol = FanControl(settings, logger)

    # Set up a more suitable logger
    logger.log('reconfiguring logger', Logger.DEBUG)
    logger = fancontrol.reconfigure_logger()
    

if __name__ == "__main__":
    main()
