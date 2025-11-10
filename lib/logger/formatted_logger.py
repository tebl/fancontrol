from . import Logger


class FormattedLogger(Logger):
    '''
    Expands base Logger implementation with ANSI-colorization, a feature to
    me - and a nuisance to others.
    '''
    def __init__(self, log_name, filter_level=Logger.INFO, auto_flush=False, formatter=None):
        self.formatter = formatter
        super().__init__(log_name, filter_level, auto_flush)


    def set_formatter(self, formatter):
        self.formatter = formatter


    def format_logline(self, message, log_level):
        message = super().format_logline(message, log_level)
        return self.format_ansi(message, log_level)


    def format_ansi(self, message, log_level):
        if not self.formatter:
            return message
        
        format_func = self.get_for(log_level)
        if not format_func:
            return message
        
        return format_func(message)


    def get_for(self, log_level):
        if self.formatter.is_monochrome:
            return self.formatter.in_regular

        if log_level >= Logger.VERBOSE:
            return self.formatter.in_verbose
        elif log_level >= Logger.DEBUG:
            return self.formatter.in_debug
        elif log_level >= Logger.INFO:
            return self.formatter.in_info
        elif log_level >= Logger.WARNING:
            return self.formatter.in_warning
        return self.formatter.in_error