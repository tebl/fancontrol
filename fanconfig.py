#!/usr/bin/python3

import sys
import argparse
from lib import Settings, PACKAGE, PACKAGE_NAME, PACKAGE_VERSION, utils
from lib.logger import *
from lib.exceptions import *
from lib.pid_file import PIDFile
from lib.control import BaseControl
from lib import utils
from lib.config import MainContext


class FanConfig(BaseControl):
    def __init__(self, settings, logger, console, dev_debug=False):
        super().__init__(settings, logger, auto_load=False)
        self.console = console
        self.running = False
        self.dev_debug = dev_debug


    def control(self, auto_select=None):
        self.auto_select = auto_select
        self.running = True
        self.context = MainContext(self, None)
        try:
            while self.running and self.context is not None:
                self.context = self.context.interact(auto_select=self.auto_select)
        except KeyboardInterrupt:
            self.running = False
        finally:
            self.shutdown()


    def shutdown(self):
        # print('Shutting down')
        pass


    def load_configuration(self):
        return super().load_configuration()


def get_auto_keys(auto_key):
    if auto_key:
        return [c for c in auto_key]
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.description = 'Python fancontrol, spinning fans in the 21st century'
    parser.add_argument('-c', '--config-path', type=utils.is_existing_config, default='fancontrol.ini', help='Specify configuration')
    parser.add_argument('-v', '--version', action='version', version=PACKAGE, help="Show version information")
    parser.add_argument('--pid-file', type=utils.is_pid, default='fancontrol.pid', help='Specify pid path')
    parser.add_argument('-z', '--zap-pid', action='store_true', help='Remove pid if it exists')
    parser.add_argument('-a', '--auto-key', help='Auto-navigate using keys specified')
    parser.add_argument('--dev-debug', action='store_true', help='Enable some stack traces upon errors')
    utils.add_interactive_arguments(parser)
    args = parser.parse_args()

    try:
        logger = utils.get_logger(PACKAGE_NAME, args, ConsoleLogger)
        settings = Settings(args.config_path, logger, reconfigure_logger=False)
        console = utils.get_interactive_logger(PACKAGE_NAME, args, auto_flush=True)
        console.log_direct('Starting {} {}'.format(FanConfig.__name__, PACKAGE_VERSION), end='\n\n')
        with PIDFile(logger, args.pid_file, zap_if_exists=args.zap_pid):
            tune = FanConfig(settings, logger, console, dev_debug=args.dev_debug)
            tune.control(auto_select=get_auto_keys(args.auto_key))
    except ConfigurationError as e:
        console.log_error('Problem in configuration:')
        console.log_direct('\t' + str(e))
        sys.exit(1)
    except ControlException as e:
        logger.log('Uncaught exception: ' + str(e), Logger.ERROR)
        sys.exit(1)


if __name__ == "__main__":
    main()
