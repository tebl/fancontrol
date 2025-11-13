import sys
from datetime import datetime
from .. import *
from .. import utils


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


    def __init__(self, log_name, filter_level=INFO, auto_flush=False):
        self.auto_flush = auto_flush
        self.log_name = log_name
        self.set_filter(filter_level)


    def __str__(self):
        return utils.to_keypair_str(type(self).__name__, Logger.to_filter_level(self.filter_level))


    def flush(self):
        '''
        Manually flush printed information to ensure that everything is not
        currently held in any buffers. As an alternatively, you can do this
        automatically by setting self.auto_flush to True at the cost of
        performance.
        '''
        sys.stdout.flush()
        sys.stderr.flush()


    def set_filter(self, filter_level):
        self.filter_level = Logger.to_filter_value(filter_level)
        self.log(utils.to_keypair_str("configuring log level", filter_level), Logger.VERBOSE+100)


    def log(self, message, log_level=INFO, end='\n'):
        '''
        Log a message if the current filter level is below what has been
        specified.
        '''
        if self.should_log(log_level):
            print(self.format_logline(message, log_level), flush=self.auto_flush, end=end)


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
