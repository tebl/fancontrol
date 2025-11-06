from datetime import datetime
from systemd import journal
from . import *
from . import utils


class Logger:
    ERROR = 0
    WARNING = 25
    INFO = 50
    DEBUG = 75
    VERBOSE = 100

    STR_ERROR = 'ERROR'
    STR_WARNING = 'WARNING'
    STR_INFO = 'INFO'
    STR_DEBUG = 'DEBUG'
    STR_VERBOSE = 'VERBOSE'
    LEVELS = [ STR_ERROR, STR_WARNING, STR_INFO, STR_DEBUG, STR_VERBOSE]

    CONSOLE = 'CONSOLE'
    JOURNAL = 'JOURNAL'
    LOG_FILE = 'LOG'
    OUTPUTS = [ CONSOLE, JOURNAL, LOG_FILE ]


    def __init__(self, log_name, filter_level = INFO):
        self.log_name = log_name
        self.set_filter(filter_level)


    def __str__(self):
        return utils.to_keypair_str(type(self).__name__, Logger.to_filter_level(self.filter_level))


    def set_filter(self, filter_level):
        self.filter_level = Logger.to_filter_value(filter_level)
        self.log(utils.to_keypair_str("configuring log level", filter_level), Logger.VERBOSE)


    def log(self, message, log_level = INFO):
        '''
        Log a message if the current filter level is below what has been
        specified.
        '''
        if self.should_log(log_level):
            print(self.format_logline(message, log_level))


    def should_log(self, log_level):
        '''
        Check whether something should be logged based on log_level-value,
        messages that didn't make the cut will be lost in time like tears in
        rain.
        '''
        return (log_level <= self.filter_level)


    def format_logline(self, message, log_level):
        return ("[" + Logger.to_filter_level(log_level) + "] ").ljust(10) + message 


    def get_timestamp(self):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


    def to_filter_level(log_level):
        '''
        Used when we want to print the filter level as part of a log somewhere,
        but there may be some accuracy lost in the conversion.
        '''
        if log_level >= Logger.VERBOSE:
            return Logger.STR_VERBOSE
        elif log_level >= Logger.DEBUG:
            return Logger.STR_DEBUG
        elif log_level >= Logger.INFO:
            return Logger.STR_INFO
        elif log_level >= Logger.WARNING:
            return Logger.STR_WARNING
        return Logger.STR_ERROR


    def to_filter_value(filter_level):
        '''
        Used when parsing filter_level as specified in settings, basically a
        string that we need to convert back to its numeric value. Or it's
        already a number and we try convert that back to an int.
        '''
        if isinstance(filter_level, str):
            match filter_level:
                case Logger.STR_ERROR:
                    return Logger.ERROR
                case Logger.STR_WARNING:
                    return Logger.WARNING
                case Logger.STR_INFO:
                    return Logger.INFO
                case Logger.STR_DEBUG:
                    return Logger.DEBUG
                case Logger.STR_VERBOSE:
                    return Logger.VERBOSE
                case _:
                    if filter_level.isnumeric():
                        return int(filter_level)
                    raise ValueError(utils.to_keypair_str("log_level not recognized", filter_level))
        return filter_level


class FormattedLogger(Logger):
    '''
    Expands base Logger implementation with ANSI-colorization, a feature to
    me - and a nuisance to others.
    '''


    def __init__(self, log_name, filter_level=Logger.INFO, formatter=None):
        self.formatter = formatter
        super().__init__(log_name, filter_level)


    def set_formatter(self, formatter):
        self.formatter = formatter


    def format_logline(self, message, log_level):
        message = super().format_logline(message, log_level)
        return self.format_ansi(message, log_level)


    def format_ansi(self, message, log_level):
        if not self.formatter:
            return message
        
        format_func = self.formatter.get_for(log_level)
        if not format_func:
            return message
        
        return format_func(message)


class ConsoleLogger(FormattedLogger):
    '''
    Intended for when scripts are running interactively. The difference from
    the base logger is that we'll omit printing the log_level when it matches
    the current setting (a feeble attempt to reduce noise). Note that we're
    still actively filtering messages.
    '''


    def __init__(self, log_name, filter_level=Logger.INFO, formatter=None):
        super().__init__(log_name, filter_level, formatter)


    def set_filter(self, filter_level):
        '''
        Configures the current log filter level, any logged items above this
        level will be discarded. As ConsoleLogger is intended for running
        interactively, we'll always have Logger.INFO as an upper bounds. 
        '''
        if Logger.to_filter_value(filter_level) < Logger.INFO:
            return super().set_filter(Logger.INFO)
        return super().set_filter(filter_level)


    def format_logline(self, message, log_level):
        if log_level == Logger.INFO:
            return self.format_ansi(message, log_level)
        return super().format_logline(message, log_level)


class InteractiveLogger(ConsoleLogger):
    '''
    Similar to ConsoleLogger except we're only relying on colorized output to
    tell entries apart.
    '''


    def __init__(self, log_name, filter_level=Logger.INFO, formatter=None):
        super().__init__(log_name, filter_level, formatter)


    def format_logline(self, message, log_level):
        '''
        Ensures that we can tell things apart before logging them, if we're not
        sure we use ConsoleLogger function to ensure that we're adding tags
        instead.
        '''
        if self.formatter and not self.formatter.is_monochrome:
            return self.format_ansi(message, log_level)
        return super().format_logline(message, log_level)


class LogfileLogger(FormattedLogger):
    '''
    Placeholder until we can put something real in here, so for now let's just
    pretend this is here so that you'd have a nicely formatted file when output
    is redirected somewhere.
    '''

    def __init__(self, log_name, filter_level=Logger.INFO, formatter=None):
        super().__init__(log_name, filter_level, formatter)


    def log(self, message, log_level):
        if self.should_log(log_level):
            print('{} {}: {}'.format(
                    self.get_timestamp(),
                    self.log_name, 
                    self.format_logline(message, log_level)
                )
            )


class ANSIFormatter:
    MONOCHROME = "MONO"
    BASIC = "BASIC"
    EXPANDED = "EXPANDED"
    ALLOWED = [ MONOCHROME, BASIC, EXPANDED ]

    FG_BASE = 30
    FG_BRIGHT = 90

    BG_BASE = 40
    BG_BRIGHT = 100

    COLOUR_BLACK = 0
    COLOUR_RED = 1
    COLOUR_GREEN = 2
    COLOUR_YELLOW = 3
    COLOUR_BLUE = 4
    COLOUR_MAGENTA = 5
    COLOUR_CYAN = 6
    COLOUR_WHITE = 7


    def __init__(self, features=BASIC):
        self.set_features(features)
            
    
    def set_features(self, features):
        self.is_monochrome = (features == self.MONOCHROME)
        self.use_16 = (features == self.BASIC) and not self.is_monochrome
        self.use_256 = (features == self.EXPANDED) and not self.is_monochrome


    def ansi_code(self, code):
        if type(code) is list:
            code = ';'.join([str(v) for v in code])
        return '\x1b[' + str(code) +'m'


    def ansi_wrap(self, codes, text):
        return self.ansi_code(codes) + text + self.ansi_code(0)


    def colour(self, base, offset):
        return base + offset
    

    def fg_colour(self, offset, bright=False):
        if bright:
            return self.colour(self.FG_BASE, offset)
        return self.colour(self.FG_BRIGHT, offset)


    def bg_colour(self, offset, bright=False):
        if bright:
            return self.colour(self.BG_BASE, offset)
        return self.colour(self.BG_BRIGHT, offset)


    def fg_colour_256(self, colour_number):
        return [38, 5, colour_number]


    def bg_colour_256(self, colour_number):
        return [48, 5, colour_number]


    def in_regular(self, str):
        return str


    def in_verbose(self, str):
        if self.use_256:
            return self.ansi_wrap(self.fg_colour_256(242), str)
        return self.ansi_wrap([2, self.fg_colour(self.COLOUR_BLACK)], str)


    def in_debug(self, str):
        if self.use_256:
            return self.ansi_wrap(self.fg_colour_256(248), str)
        return self.ansi_wrap([2, self.fg_colour(self.COLOUR_BLACK)], str)


    def in_info(self, str):
        if self.use_256:
            return self.ansi_wrap(self.fg_colour_256(255), str)
        return self.ansi_wrap(self.fg_colour(self.COLOUR_WHITE), str)


    def in_warning(self, str):
        if self.use_256:
            return self.ansi_wrap(self.fg_colour_256(220), str)
        return self.ansi_wrap(self.fg_colour(self.COLOUR_YELLOW), str)


    def in_error(self, str):
        if self.use_256:
            return self.ansi_wrap(self.fg_colour_256(160), str)
        return self.ansi_wrap(self.fg_colour(self.COLOUR_RED), str)


    def get_for(self, log_level):
        if self.is_monochrome:
            return self.in_regular

        if log_level >= Logger.VERBOSE:
            return self.in_verbose
        elif log_level >= Logger.DEBUG:
            return self.in_debug
        elif log_level >= Logger.INFO:
            return self.in_info
        elif log_level >= Logger.WARNING:
            return self.in_warning
        return self.in_error


class JournalLogger(Logger):
    '''
    Version of the logger that interfaces with systemd-journal
    '''


    def __init__(self, log_name, filter_level=Logger.INFO):
        super().__init__(log_name, filter_level)


    def log(self, message, log_level = Logger.INFO):
        '''
        Log a message if the current filter level is below what has been
        specified. Such messages will be lost in time, like tears in rain.
        '''
        priority = self.get_priority(log_level)
        if priority == None:
            return
        if not self.should_log(log_level):
            return

        journal.send(
            self.format_logline(message, log_level),
            SYSLOG_IDENTIFIER=self.log_name,
            PRIORITY=priority
        )
    

    def get_priority(self, log_level):
        if log_level >= Logger.VERBOSE:
            return journal.LOG_DEBUG
        elif log_level >= Logger.DEBUG:
            return journal.LOG_DEBUG
        elif log_level >= Logger.INFO:
            return journal.LOG_INFO
        elif log_level >= Logger.WARNING:
            return journal.LOG_WARNING
        return journal.LOG_ERR


    def format_logline(self, message, log_level):
        return '[{}] {}'.format(Logger.to_filter_level(log_level), message)


class LoggerMixin:
    def set_logger(self, logger) -> None:
        self.logger = logger


    def log_error(self, *args) -> None:
        self.logger.log(' '.join(args), Logger.ERROR)    


    def log_warning(self, *args) -> None:
        self.logger.log(' '.join(args), Logger.WARNING)    


    def log_info(self, *args) -> None:
        self.logger.log(' '.join(args), Logger.INFO)


    def log_debug(self, *args) -> None:
        self.logger.log(' '.join(args), Logger.DEBUG)


    def log_verbose(self, *args) -> None:
        self.logger.log(' '.join(args), Logger.VERBOSE)


    def configure_logger(self, filter_level) -> None:
        self.logger.set_filter(filter_level)
