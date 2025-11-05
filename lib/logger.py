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
        if log_level >= Logger.VERBOSE:
            return 'VERBOSE'
        elif log_level >= Logger.DEBUG:
            return 'DEBUG'
        elif log_level >= Logger.INFO:
            return 'INFO'
        elif log_level >= Logger.WARNING:
            return 'WARNING'
        return 'ERROR'


    def to_filter_value(filter_level):
        if isinstance(filter_level, str):
            match filter_level:
                case 'ERROR':
                    return Logger.ERROR
                case 'WARNING':
                    return Logger.WARNING
                case 'INFO':
                    return Logger.INFO
                case 'DEBUG':
                    return Logger.DEBUG
                case 'VERBOSE':
                    return Logger.VERBOSE
                case _:
                    raise ValueError(utils.to_keypair_str("log_level not recognized", filter_level))
        return filter_level


class ConsoleLogger(Logger):
    '''
    Intended for when scripts are running interactively. The difference from
    the base logger is that we'll omit printing the log_level when it matches
    the current setting (a feeble attempt to reduce noise). Note that we're
    still actively filtering messages.
    '''


    def __init__(self, log_name, filter_level=Logger.INFO):
        super().__init__(log_name, filter_level)


    def set_filter(self, filter_level):
        '''
        Configures the current log filter level, any logged items above this
        level will be discarded. As ConsoleLogger is intended for running
        interactively, we'll always have Logger.INFO as an upper bounds. 
        '''
        if Logger.to_filter_value(filter_level) < Logger.INFO:
            return super().set_filter(Logger.INFO)
        return super().set_filter(filter_level)


    def log(self, message, log_level = Logger.INFO):
        if log_level == Logger.INFO:
            print(message)
            return
        super().log(message, log_level)


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


class LogfileLogger(Logger):
    '''
    Placeholder until we can put something real in here, so for now let's just
    pretend this is here so that you'd have a nicely formatted file when output
    is redirected somewhere.
    '''

    def __init__(self, log_name, filter_level=Logger.INFO):
        super().__init__(log_name, filter_level)


    def log(self, message, log_level):
        if self.should_log(log_level):
            print('{} {}: {}'.format(
                    self.get_timestamp(),
                    self.log_name, 
                    self.format_logline(message, log_level)
                )
            )


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
