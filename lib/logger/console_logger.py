from . import Logger, FormattedLogger


class ConsoleLogger(FormattedLogger):
    '''
    Intended for when scripts are running interactively. The difference from
    the base logger is that we'll omit printing the log_level when it matches
    the current setting (a feeble attempt to reduce noise). Note that we're
    still actively filtering messages.
    '''
    def __init__(self, log_name, filter_level=Logger.INFO, auto_flush=False, formatter=None):
        super().__init__(log_name, filter_level, auto_flush=auto_flush, formatter=formatter)


    def set_filter(self, filter_level):
        '''
        Configures the current log filter level, any logged items above this
        level will be discarded. As ConsoleLogger is intended for running
        interactively, we'll always have Logger.INFO as an upper bounds. 
        '''
        if Logger.to_filter_value(filter_level) < Logger.INFO:
            return super().set_filter(Logger.INFO)
        return super().set_filter(filter_level)