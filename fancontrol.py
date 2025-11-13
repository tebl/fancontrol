#!/usr/bin/python3

import sys
import argparse
import os
import time
from lib import Settings, PACKAGE, PACKAGE_NAME, utils, ANSIFormatter
from lib.logger import *
from lib.exceptions import *
from lib.interrupt import InterruptHandler
from lib.pid_file import PIDFile
from lib.control import BaseControl, RawSensor, Sensor, PWMRequest, PWMSensor, FanSensor, TemperatureSensor, Fan
from lib.scheduler import MicroScheduler


class FanControl(BaseControl):
    def __init__(self, settings, logger):
        super().__init__(settings, logger)
        self.running = False


    def control(self, interrupt_handler):
        self.running = True
        self.scheduler = MicroScheduler(self.logger, self.delay)

        self.log_info('{} starting'.format(self))
        self.__setup()
        while self.running:
            try:
                self.scheduler.set_next()
                self.__control()

                while self.running and not self.scheduler.was_passed():
                    if self.check_interrupt(interrupt_handler):
                        time.sleep(.3)
                        self.__u_control()
            except KeyboardInterrupt:
                self.running = False
            except SensorException as e:
                self.log_error('{} encountered a sensor error, halting... ({})'.format(self, e))
                self.running = False
        self.__shutdown()
        self.log_info('{} stopped'.format(self))


    def check_interrupt(self, handler):
        if handler.interrupted:
            self.log_warning('{} INT received, halting...'.format(self))
            self.running = False
        return self.running


    def set_logger(self, logger):
        self.scheduler.set_logger(logger)
        return super().set_logger(logger)


    def __setup(self):
        self.log_verbose('{} setup'.format(self))
        try:
            self.__update_sensors()
            self.__setup_fans()
            self.__setup_pwm()
        except ControlRuntimeError as e:
            self.log_error('{} encountered during setup phase, halting...'.format(e))
            self.running = False
            self.__failsafe()


    def __failsafe(self):
        self.log_error('failsafe triggered, attempting to crash in a safe place')
        self.__shutdown(ignore_exceptions=True)


    def __setup_fans(self):
        for fan in self.fans:
            fan.setup()


    def __setup_pwm(self):
        for i, (name, sensor) in enumerate(self.sensors.items()):
            if type(sensor) is PWMSensor:
                sensor.setup()


    def __control(self):
        '''
        Called once at the start of every update cycle, takes care of updating
        and then allowing each component to plan their next move.
        '''
        self.__update_sensors()
        self.__update_fans()
        self.__control_done()


    def __u_control(self):
        for i, (name, sensor) in enumerate(self.outputs.items()):
            sensor.u_tick()


    def __update_sensors(self):
        for i, (name, sensor) in enumerate(self.sensors.items()):
            sensor.update()


    def __update_fans(self):
        for fan in self.fans:
            fan.update()


    def __control_done(self):
        for i, (name, output) in enumerate(self.outputs.items()):
            output.plan_ahead()


    def __shutdown(self, ignore_exceptions = False):
        self.log_verbose('{} shutdown'.format(self))
        for method in [self.__shutdown_fans, self.__shutdown_pwm]:
            try:
                self.log_verbose('{} running {}...'.format(self, method.__name__))
                result = method(ignore_exceptions)
                self.log_verbose('{} ... {}'.format(self, result))
            except ControlRuntimeError as e:
                self.log_error('{} encountered {} during shutdown phase!'.format(self, e))


    def __shutdown_fans(self, ignore_exceptions = False):
        for fan in self.fans:
            fan.shutdown(ignore_exceptions)
        return 'OK'


    def __shutdown_pwm(self, ignore_exceptions = False):
        for i, (name, output) in enumerate(self.outputs.items()):
            output.shutdown(ignore_exceptions)
        return 'OK'
    

def perform_verify(run_verify, logger, settings):
    '''
    Loads up the configuration then returns, this hopefully will allow us to
    check if the runtime environment is somewhat sane before doing something
    as insane as for instance stopping the CPU-fan. 
    '''
    if not run_verify:
        return False

    try:
        logger.log(PACKAGE)
        FanControl(settings, logger)
        logger.log('OK.')
    except ConfigurationError as e:
        logger.log(str(e), Logger.ERROR)
        sys.exit(1)
    return True


def reconfigure_logger(args, logger, filter_level, settings):
    if args.log_console:
        logger.set_filter(filter_level)
    elif args.log_journal:
        logger = JournalLogger(PACKAGE_NAME, filter_level)
    elif args.log_logformat:
        logger = LogfileLogger(PACKAGE_NAME, filter_level)
    else:
        match settings.log_using:
            case Logger.JOURNAL:
                logger = JournalLogger(PACKAGE_NAME, filter_level)
            case Logger.LOG_FILE:
                logger = LogfileLogger(PACKAGE_NAME, filter_level)
            case Logger.CONSOLE:
                if type(logger) is ConsoleLogger:
                    logger.set_filter(filter_level)
                else:
                    logger = ConsoleLogger(PACKAGE_NAME, filter_level)
            case _:
                logger.log(utils.to_keypair_str('Encountered unknown logger value', settings.log_using), Logger.WARNING)

    if isinstance(logger, FormattedLogger):
        features = settings.log_formatter
        if args.monochrome:
            features = ANSIFormatter.MONOCHROME
        if args.less_colours:
            features = ANSIFormatter.BASIC
        if args.more_colours:
            features = ANSIFormatter.EXPANDED
        logger.set_formatter(ANSIFormatter(features))

    return logger


def get_logger(logger, args, settings):
    filter_level = utils.get_filter_level(settings.log_level, args.debug, args.verbose)
    logger = reconfigure_logger(args, logger, filter_level, settings)
    logger.log('Initialized ' + str(logger), Logger.DEBUG)
    return logger


def main():
    parser = argparse.ArgumentParser()
    parser.description = 'Python fancontrol, spinning fans in the 21st century'
    parser.add_argument('-c', '--config-path', type=utils.is_existing_config, default='fancontrol.ini', help='Specify configuration')
    parser.add_argument('-v', '--version', action='version', version=PACKAGE, help="Show version information")
    parser.add_argument('--pid-file', type=utils.is_pid, default='fancontrol.pid', help='Specify pid path')
    parser.add_argument('-z', '--zap-pid', action='store_true', help='Remove pid if it exists')
    parser.add_argument('--verify', action='store_true', help='Fancontrol will load and check configuration before exiting')
    parser_logging = parser.add_mutually_exclusive_group()
    parser_logging.add_argument('--log-console', action='store_true', help='Fancontrol will only log to console')
    parser_logging.add_argument('--log-logformat', action='store_true', help='Logs are printed, but now in with timestamps')
    parser_logging.add_argument('--log-journal', action='store_true', help='Logs are sent to systemd-journal')
    utils.add_interactive_arguments(parser)
    args = parser.parse_args()

    try:
        current_logger = utils.get_interactive_logger(PACKAGE_NAME, args)
        settings = Settings(args.config_path, current_logger)

        # If we're only running a verification of the configuration
        if perform_verify(args.verify, current_logger, settings):
            sys.exit(0)

        # From this point on the assumption is that we are no longer running
        # interactively. First step is to switch to a more suitable logger.
        current_logger = get_logger(current_logger, args, settings)

        with PIDFile(current_logger, args.pid_file, zap_if_exists=args.zap_pid):
            fancontrol = FanControl(settings, current_logger)
            with InterruptHandler() as handler:
                fancontrol.control(handler)
    except ControlException as e:
        current_logger.log('Uncaught exception: ' + str(e), Logger.ERROR)
        sys.exit(1)


if __name__ == "__main__":
    main()
