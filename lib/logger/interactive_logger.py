from . import Logger, ConsoleLogger


class InteractiveLogger(ConsoleLogger):
    '''
    Similar to ConsoleLogger except we're only relying on colorized output to
    tell entries apart.
    '''
    def __init__(self, log_name, filter_level=Logger.INFO, auto_flush=False, formatter=None):
        super().__init__(log_name, filter_level, auto_flush, formatter)


    def format_logline(self, message, log_level):
        '''
        Ensures that we can tell things apart before logging them, if we're not
        sure we use ConsoleLogger function to ensure that we're adding tags
        instead.
        '''
        if self.formatter and not self.formatter.is_monochrome:
            return self.format_ansi(message, log_level)
        return super().format_logline(message, log_level)