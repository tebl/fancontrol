from . import Logger, FormattedLogger


class LogfileLogger(FormattedLogger):
    '''
    Placeholder until we can put something real in here, so for now let's just
    pretend this is here so that you'd have a nicely formatted file when output
    is redirected somewhere.
    '''
    def __init__(self, log_name, filter_level=Logger.INFO, auto_flush=False, formatter=None):
        super().__init__(log_name, filter_level, auto_flush, formatter)


    def log(self, message, log_level=Logger.INFO, end='\n'):
        if self.should_log(log_level):
            print('{} {}: {}'.format(
                    self.get_timestamp(),
                    self.log_name, 
                    self.format_logline(message, log_level)
                ), 
                flush=self.auto_flush
            )