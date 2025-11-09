from time import time
from .logger import LoggerMixin
from .exceptions import *


class MicroScheduler(LoggerMixin):
    '''
    Used to manage tasks in a non-blocking manner by managing future
    "appointments", but not really giving any guarantees beyond keeping
    things organized.
    '''
    def __init__(self, logger, step_delay, limit=None):
        self.logger = logger
        self.step_delay = step_delay
        self.set_limit(limit)
        self.clear()


    def set_limit(self, limit=None):
        self.limit = limit
        self.count = limit


    def clear(self):
        self.next_set = False
        self.last_updated = None
        self.trigger_at = None


    def set_next(self, now=None):
        '''
        Set a new point in time where we should - ideally - trigger.
        '''
        if now is None:
            now = time()
        self.__check_limit()
        self.last_updated = now
        self.trigger_at = self.last_updated + self.step_delay
        self.next_set = True
        return self


    def __check_limit(self):
        if self.limit == None:
            return
        if self.count > 0:
            self.count -= 1
            return
        raise SchedulerLimitExceeded(
            self.limit, 
            '{} could not set next step due to limit={}'.format(
                self.__class__.__name__, 
                str(self.limit)
            )
        )


    def was_passed(self, now=None):
        '''
        Performs a check as to whether the clock rolled past the next point in
        time. The weird checks are a feature, mainly so that we don't wait
        endlessly if the clock was set either forward or backwards in time -
        both mean that we have no idea where we are, so we trigger directly to
        ensure that we're actively doing what we need to.
        '''
        if not self.next_set:
            raise NotScheduledException('set_next() has not been called')

        if now is None:
            now = time()
        if now < self.last_updated:
            self.log_warning('We went back in time!')
            return True
        if (now - self.last_updated) > self.step_delay*2:
            self.log_warning('We went far into the future!')
            return True
        return now > self.trigger_at
    

    @staticmethod
    def suggest_step_delay(cycle_length, max_steps, max_length=None):
        step_length = cycle_length / max_steps
        if max_length is not None and step_length > max_length:
            return float(max_length)
        return step_length
