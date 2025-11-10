from . import Logger


class QueueLogger(Logger):
    '''
    Used when running tests
    '''
    def __init__(self, log_name, filter_level=Logger.INFO, max_entries=50):
        self.entries = []
        self.discarded = 0
        self.max_entries = max_entries
        super().__init__(log_name, filter_level)
    

    def log(self, message, log_level=Logger.INFO, end='\n'):
        if not self.should_log(log_level):
            return

        self.entries.append({'message': message, 'log_level': log_level})
        if len(self.entries) > self.max_entries:
            self.entries.pop(0)
            self.discarded += 1

    
    def clear(self):
        self.discarded += len(self.entries)
        self.entries = []


    def includes_logged(self, message, log_level):
        for entry in self.entries:
            if entry['log_level'] is not log_level:
                continue
            if message is not None and not entry['message'].startswith(message):
                continue
            return self.format_logline(entry['message'], entry['log_level'])
        return False