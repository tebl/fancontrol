from time import time
from .logger import LoggerMixin
from .exceptions import ControlRuntimeError


class MicroScheduler(LoggerMixin):
    '''
    Used to manage tasks in a non-blocking manner by managing future
    "appointments", but not really giving any guarantees beyond keeping
    things organized.
    '''


    def __init__(self, logger, step_delay, limit = None):
        self.logger = logger
        self.step_delay = step_delay
        self.limit = limit
        self.last_updated = None
        self.trigger_at = None


    def set_next(self):
        '''
        Set a new point in time where we should - ideally - trigger.
        '''
        self.last_updated = time()
        self.trigger_at = self.last_updated + self.step_delay
        return self


    def was_passed(self):
        '''
        Performs a check as to whether the clock rolled past the next point in
        time. The weird checks are a feature, mainly so that we don't wait
        endlessly if the clock was set either forward or backwards in time -
        both mean that we have no idea where we are, so we trigger directly to
        ensure that we're actively doing what we need to.
        '''
        now = time()
        if now < self.last_updated:
            self.log_warning('We went back in time!')
            return True
        if (now - self.last_updated) > self.step_delay*2:
            self.log_warning('We went into the future!')
            return True
        return now > self.trigger_at