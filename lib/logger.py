class Logger:
    ERROR = 0
    WARNING = 25
    INFO = 50
    DEBUG = 100


    def __init__(self, log_level = INFO):
        self.set_level(log_level)


    def set_level(self, log_level):
        if isinstance(log_level, str):
            match log_level:
                case 'ERROR':
                    log_level = Logger.ERROR
                case 'WARNING':
                    log_level = Logger.WARNING
                case 'INFO':
                    log_level = Logger.INFO
                case 'DEBUG':
                    log_level = Logger.DEBUG
                case _:
                    raise ValueError(Logger.to_key_value("log_level not recognized", log_level))
        self.filter_level = log_level


    def log(self, log_level, message):
        if (log_level <= self.filter_level):
            print(message)


    def to_key_value(key, value):
        return str(key) + " (" + str(value) + ")"


class ConsoleLogger(Logger):
    def __init__(self):
        super().__init__(None)

    def log(self, log_level, message):
        print(message)


class LoggerMixin:
    def set_logger(self, logger) -> None:
        self.logger = logger


    def log_error(self, *args) -> None:
        self.logger.log(Logger.ERROR, ' '.join(args))    


    def log_warning(self, *args) -> None:
        self.logger.log(Logger.WARNING, ' '.join(args))    


    def log_info(self, *args) -> None:
        self.logger.log(Logger.INFO, ' '.join(args))    


    def log_debug(self, *args) -> None:
        self.logger.log(Logger.DEBUG, ' '.join(args))


    def configure_logger(self, filter_level) -> None:
        self.logger.set_level(filter_level)
        self.log_debug(Logger.to_key_value("configuring log level", filter_level))
