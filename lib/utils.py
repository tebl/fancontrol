import argparse
import os.path
from .logger import Logger, InteractiveLogger, FormattedLogger
from .ansi import ANSIFormatter
from . import *

def to_keypair_str(key, value):
    return str(key) + " (" + str(value) + ")"


def remap_int(value, in_min, in_max, out_min, out_max):
    return out_min + (float(value - in_min) / float(in_max - in_min)) * (out_max - out_min)


def is_pid(pid_path):
    '''
    Check that the specified pid path looks valid, mainly by checking for
    the extension.
    '''
    if not pid_path.lower().endswith(('.pid')):
        raise argparse.ArgumentError(utils.to_keypair_str('Unknown extension specified', pid_path))
    return pid_path


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


def is_existing_config(config_path):
    '''
    Check that the specified configuration file actually exists and has the
    right extension, but beyond that we're not looking at the contents of it.
    '''
    if not os.path.isfile(config_path):
        raise argparse.ArgumentError(utils.to_keypair_str('No suitable file specified', config_path))
    if not config_path.lower().endswith(('.ini')):
        raise argparse.ArgumentError(utils.to_keypair_str('Unknown extension specified', config_path))
    return config_path


def get_filter_level(current, set_debug, set_verbose):
    levels = [ Logger.to_filter_value(current) ]
    if set_debug:
        levels.append(Logger.DEBUG)
    if set_verbose:
        levels.append(Logger.VERBOSE)
    return max(levels)


def add_interactive_arguments(parser):
    '''
    Add argument parser arguments as expected by get_interactive_logger(args)
    '''
    parser.add_argument('--debug', action='store_true', help='Enable debug messages')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose debug messages')
    parser_colorization = parser.add_mutually_exclusive_group()
    parser_colorization.add_argument('--monochrome', action='store_true', help='Remove colorization from output')
    parser_colorization.add_argument('--less-colours', action='store_true', help='Limit colorization to 16 colours')
    parser_colorization.add_argument('--more-colours', action='store_true', help='Allow colorization to use 256 colours')


def get_interactive_logger(name, args, auto_flush=False):
    '''
    Get logger suitable for interactive use, colour may cause differences in
    the output - this is controlled via the following arguments:
        - args.debug
        - args.verbose
        - args.monochrome
        - args.less_colours
        - args.more_colours
    '''
    filter_level = get_filter_level(Logger.INFO, args.debug, args.verbose)
    logger = InteractiveLogger(name, filter_level=filter_level, auto_flush=auto_flush)

    if isinstance(logger, FormattedLogger):
        features = ANSIFormatter.EXPANDED
        if args.monochrome:
            features = ANSIFormatter.MONOCHROME
        elif args.less_colours:
            features = ANSIFormatter.BASIC
        elif args.more_colours:
            # Already covered indirectly, but let's just put it here so that I
            # don't immediately forget.
            features = ANSIFormatter.EXPANDED
        logger.set_formatter(ANSIFormatter(features))

    return logger
