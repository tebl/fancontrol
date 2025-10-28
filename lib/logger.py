class Logger:
    ERROR = 0
    WARNING = 25
    INFO = 50
    DEBUG = 100


    def __init__(self, filter_level = INFO):
        self.set_filter(filter_level)


    def set_filter(self, filter_level):
        if isinstance(filter_level, str):
            match filter_level:
                case 'ERROR':
                    filter_level = Logger.ERROR
                case 'WARNING':
                    filter_level = Logger.WARNING
                case 'INFO':
                    filter_level = Logger.INFO
                case 'DEBUG':
                    filter_level = Logger.DEBUG
                case _:
                    raise ValueError(Logger.to_key_value("log_level not recognized", filter_level))
        self.filter_level = filter_level


    def log(self, message, log_level):
        if (log_level <= self.filter_level):
            print(Logger.format_logline(message, log_level))


    def to_key_value(key, value):
        return str(key) + " (" + str(value) + ")"
    

    def format_logline(message, log_level):
        return ("[" + Logger.to_filter_level(log_level) + "] ").ljust(10) + message 


    def to_filter_level(log_level):
        if log_level >= Logger.DEBUG:
            return 'DEBUG'
        elif log_level >= Logger.INFO:
            return 'INFO'
        elif log_level >= Logger.WARNING:
            return 'WARNING'
        return 'ERROR'


class ConsoleLogger(Logger):
    def __init__(self, filter_level = Logger.INFO):
        super().__init__(filter_level)


    def log(self, message, log_level):
        if (self.filter_level != log_level):
            super().log(message, log_level)
            return
        print(message)


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


    def configure_logger(self, filter_level) -> None:
        self.logger.set_filter(filter_level)
        self.log_debug(Logger.to_key_value("configuring log level", filter_level))
