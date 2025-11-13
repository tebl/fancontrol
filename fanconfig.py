#!/usr/bin/python3

import sys
import argparse
import os
import time
from lib import Settings, PACKAGE, PACKAGE_NAME, PACKAGE_VERSION, utils
from lib.logger import *
from lib.exceptions import *
from lib.pid_file import PIDFile
from lib.control import BaseControl, RawSensor, Sensor, PWMRequest, PWMSensor, FanSensor, TemperatureSensor, Fan
from lib.scheduler import MicroScheduler
from lib import utils


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


class MainContext(InteractiveContext):
    def __init__(self, *args):
        super().__init__(*args)


    def interact(self):
        self.summarise([
            ['Delay', 'Controller updates every {} seconds'.format(self.fan_config.delay)],
            ['Device', self.fan_config.get_path()],
            [self.SUBKEY_INDENT + 'Path checked', self.fan_config.dev_path],
            [self.SUBKEY_INDENT + 'Driver checked', self.fan_config.dev_name]
        ])

        self.message()
        self.message('Listing available definitions:')
        input = self.console.prompt_choices(self.__get_prompt_builder())
        match input:
            case None | 'x':
                return self.parent
            case _:
                fan = self.prompt_values[input]
                self.message('Fan {} selected'.format(fan.get_title()), end='\n\n')
                return FanContext(self.fan_config, self, fan=fan)
        return self


    def __get_prompt_builder(self):
        builder = PromptBuilder(self.console)
        self.prompt_values = {}
        for fan in self.fan_config.fans:
            key = builder.set_next(fan.get_title())
            self.prompt_values[key] = fan
        builder.add_exit()
        return builder


class FanContext(InteractiveContext):
    def __init__(self, *args, fan):
        self.fan = fan
        super().__init__(*args)


    def interact(self):
        self.summarise([
            ['Controlled by', self.fan.device],
            [self.SUBKEY_INDENT + 'Minimum', self.format_pwm(self.fan.pwm_min)],
            [self.SUBKEY_INDENT + 'Maximum', self.format_pwm(self.fan.pwm_max)],
            [self.SUBKEY_INDENT + 'Start', self.format_pwm(self.fan.pwm_start)],
            [self.SUBKEY_INDENT + 'Stop', self.format_pwm(self.fan.pwm_stop)],
            ['Based on', self.fan.sensor],
            [self.SUBKEY_INDENT + 'Minimum', self.format_temp(self.fan.sensor_min)],
            [self.SUBKEY_INDENT + 'Maximum', self.format_temp(self.fan.sensor_max)]
        ])

        input = self.console.prompt_choices(self.__get_prompt_builder(), prompt=self.fan.get_title())
        match input:
            case None | 'x':
                return self.parent
            case _:
                self.message('You entered ' + input)
                return self
        return self
    




    def __get_prompt_builder(self):
        builder = PromptBuilder(self.console)
        # self.prompt_values = {}
        # for fan in self.fan_config.fans:
        #     key = builder.set_next(fan.get_title())
        #     self.prompt_values[key] = fan
        builder.add_back()
        return builder


    # def validate_input(self, value):
    #     return value == 'end'


class FanConfig(BaseControl):
    def __init__(self, settings, logger, console):
        super().__init__(settings, logger)
        self.__read_configuration()
        self.console = console
        self.running = False


    def control(self):
        self.running = True
        self.context = MainContext(self, None)
        try:
            while self.running and self.context is not None:
                self.context = self.context.interact()
        except KeyboardInterrupt:
            self.running = False
        finally:
            self.shutdown()


    def shutdown(self):
        print('Shutting down')
        pass


    def __read_configuration(self):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.description = 'Python fancontrol, spinning fans in the 21st century'
    parser.add_argument('-c', '--config-path', type=utils.is_existing_config, default='fancontrol.ini', help='Specify configuration')
    parser.add_argument('-v', '--version', action='version', version=PACKAGE, help="Show version information")
    parser.add_argument('--pid-file', type=utils.is_pid, default='fancontrol.pid', help='Specify pid path')
    parser.add_argument('-z', '--zap-pid', action='store_true', help='Remove pid if it exists')
    utils.add_interactive_arguments(parser)
    args = parser.parse_args()

    try:
        logger = utils.get_logger(PACKAGE_NAME, args, ConsoleLogger)
        settings = Settings(args.config_path, logger, reconfigure_logger=False)
        console = utils.get_interactive_logger(PACKAGE_NAME, args, auto_flush=True)
        console.log_direct('Starting {} {}'.format(FanConfig.__name__, PACKAGE_VERSION))
        with PIDFile(logger, args.pid_file, zap_if_exists=args.zap_pid):
            tune = FanConfig(settings, logger, console)
            tune.control()
    except ConfigurationError as e:
        console.log_error('Problem in configuration:')
        console.log_direct('\t' + str(e))
        sys.exit(1)
    except ControlException as e:
        logger.log('Uncaught exception: ' + str(e), Logger.ERROR)
        sys.exit(1)


if __name__ == "__main__":
    main()
