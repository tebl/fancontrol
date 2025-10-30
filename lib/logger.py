class Logger:
    ERROR = 0
    WARNING = 25
    INFO = 50
    DEBUG = 75
    VERBOSE = 100


    def __init__(self, filter_level = INFO):
        self.set_filter(filter_level)


    def __str__(self):
        return Logger.to_key_value(type(self).__name__, Logger.to_filter_level(self.filter_level))


    def set_filter(self, filter_level):
        self.filter_level = Logger.to_filter_value(filter_level)
        self.log(Logger.to_key_value("configuring log level", filter_level), Logger.VERBOSE)


    def log(self, message, log_level = INFO):
        '''
        Log a message if the current filter level is below what has been
        specified. Such messages will be lost in time, like tears in rain.
        '''
        if (log_level <= self.filter_level):
            print(Logger.format_logline(message, log_level))


    def to_key_value(key, value):
        return str(key) + " (" + str(value) + ")"
    

    def format_logline(message, log_level):
        return ("[" + Logger.to_filter_level(log_level) + "] ").ljust(10) + message 


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
                    raise ValueError(Logger.to_key_value("log_level not recognized", filter_level))
        return filter_level


class ConsoleLogger(Logger):
    '''
    Intended for when scripts are running interactively. The difference from
    the base logger is that we'll omit printing the log_level when it matches
    the current setting in a feeble attempt to reduce noise. Note that we're
    still actively filtering messages.
    '''

    def __init__(self, filter_level = Logger.INFO):
        super().__init__(filter_level)


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
        else:
            super().log(message, log_level)


class LogfileLogger(Logger):
    '''
    Placeholder until we can put something real in here
    '''

    def __init__(self, filter_level = Logger.INFO):
        super().__init__(filter_level)


    def log(self, message, log_level):
        if (log_level <= self.filter_level):
            print('[LOG] ' + Logger.format_logline(message, log_level))


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
