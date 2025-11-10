from systemd import journal
from . import Logger

class JournalLogger(Logger):
    '''
    Version of the logger that interfaces with systemd-journal
    '''
    def __init__(self, log_name, filter_level=Logger.INFO):
        super().__init__(log_name, filter_level)


    def log(self, message, log_level=Logger.INFO, end='\n'):
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