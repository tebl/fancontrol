from time import time
from .logger import LoggerMixin


class MicroScheduler(LoggerMixin):
    def __init__(self, logger, step_delay):
        self.logger = logger
        self.step_delay = step_delay
        self.last_updated = None
        self.trigger_at = None


    def set_next(self):
        self.last_updated = time()
        self.trigger_at = self.last_updated + self.step_delay
        return self


    def was_passed(self):
        now = time()
        if now < self.last_updated:
            self.log_warning('We went back in time!')
            return True
        if (now - self.last_updated) > self.step_delay*2:
            self.log_warning('We went into the future!')
            return True
        return now > self.trigger_at
