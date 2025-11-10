from . import Logger


class LoggerMixin:
    def set_logger(self, logger) -> None:
        self.logger = logger


    def log_error(self, *args, end='\n') -> None:
        self.logger.log(' '.join(args), Logger.ERROR, end=end)    


    def log_warning(self, *args, end='\n') -> None:
        self.logger.log(' '.join(args), Logger.WARNING, end=end)    


    def log_info(self, *args, end='\n') -> None:
        self.logger.log(' '.join(args), Logger.INFO, end=end)


    def log_debug(self, *args, end='\n') -> None:
        self.logger.log(' '.join(args), Logger.DEBUG, end=end)


    def log_verbose(self, *args, end='\n') -> None:
        self.logger.log(' '.join(args), Logger.VERBOSE, end=end)


    def configure_logger(self, filter_level) -> None:
        self.logger.set_filter(filter_level)