import argparse
import math
import os.path
from .logger import Logger, InteractiveLogger, FormattedLogger
from .ansi import ANSIFormatter
from . import *


ACRONYMS = [ ]
'Acronyms used as default by the module, add anything expected to be globally true'


class Acronym:
    def __init__(self, value):
        self.value = value


    def __str__(self):
        return self.value


def to_sentence(*args, acronyms=None, first=True):
    '''
    Convert a series of words into something resembling a sentence, in essence
    avoiding the need to redefine strings based on the capitalization of the
    first letter. Words that contain spaces will be split up and processed
    separately, but only if it isn't already an acronym.
    '''
    if acronyms is None:
        acronyms = ACRONYMS
    words = list(args)
    for index, word in enumerate(words):
        if not is_acronym(word, acronyms):
            parts = word.split()
            if len(parts) == 1:
                words[index] = word.lower() if not first else word[0].upper() + word[1:]
            else:
                words[index] = to_sentence(*parts, acronyms=acronyms, first=False)
        else:
            words[index] = str(word)
        first = False
    return ' '.join(words)


def is_acronym(word, acronyms=None):
    '''
    Check whether the specified word is an acronym, meaning that it's either
    included in the list of acronyms passed to it - or it's entirely in caps.
    '''
    if type(word) is Acronym:
        return True
    if acronyms is None:
        acronyms = ACRONYMS
    if word in acronyms:
        return True
    return word.isupper()


def to_keypair_str(key, value):
    return str(key) + " (" + str(value) + ")"


def remap_int(value, in_min, in_max, out_min, out_max):
    '''
    Similar to Arduino map-function, used to map one integer range onto another.
    '''
    return out_min + (float(value - in_min) / float(in_max - in_min)) * (out_max - out_min)


def format_pwm(value):
    return '({}/255)'.format(str(value).rjust(3))


def format_rpm(value):
    return '{} RPM'.format(str(value))


def format_celsius(value):
    return '{}°C'.format(str(value))


def pad_number(value, steps = 10):
    '''
    Pads out a number to a certain limit, mainly used in order to conform to
    certain widths.
    '''
    return steps * math.ceil(value / steps)


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


def get_logger(name, args, logger_class, auto_flush=False):
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
    logger = logger_class(name, filter_level=filter_level, auto_flush=auto_flush)

    if isinstance(logger, FormattedLogger):
        features = ANSIFormatter.EXPANDED
        if args.monochrome:
            features = ANSIFormatter.MONOCHROME
        elif args.less_colours:
            features = ANSIFormatter.BASIC
        elif args.more_colours:
            # Already covered indirectly, but let's just put it here so that I
            # don't forget about it tomorrow.
            features = ANSIFormatter.EXPANDED
        logger.set_formatter(ANSIFormatter(features))

    return logger


def get_interactive_logger(name, args, auto_flush=False):
    return get_logger(name, args, InteractiveLogger, auto_flush=auto_flush)


def get_console_logger(name, args, auto_flush=False):
    return get_logger(name, args, ConsoleLogger, auto_flush=auto_flush)
