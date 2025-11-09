from .utils import to_keypair_str


class ControlException(Exception):
    '''
    Base class for all of the exceptions used within the project, offers
    nothing beyond a way to differentiate exception origin.
    '''
    def __init__(self, *args):
        super().__init__(*args)


class ConfigurationError(ControlException):
    '''
    ConfigurationError should _only_ be used in the application setup phase,
    used to notify that something looks iffy before attempting to take control
    over anything (leaving them controlled by chipset).

    When actually running, see ControlRuntimeError.
    '''
    def __init__(self, message, details = None):
        if details:
            super().__init__(to_keypair_str(message, details))
        else:
            super().__init__(message)


class ControlRuntimeError(ControlException):
    '''
    Used to signal some sort of unexpected result when the program is actively
    handling the control over fans.
    '''
    def __init__(self, message):
        super().__init__(message)
        self.message = message


    def __str__(self):
        return '{}({})'.format(self.__class__.__name__, self.message)


class SensorException(ControlRuntimeError):
    '''
    Some sort of error occurred when reading from or writing to a configured
    sensor. 
    '''


class SchedulerException(ControlRuntimeError):
    '''
    Base exception used with MicroScheduler
    '''


class NotScheduledException(SchedulerException):
    '''
    Used when checking if the next timestamp was passed, but we haven't called
    next_step yet - or - we've called clear on it. 
    '''


class SchedulerLimitExceeded(SchedulerException):
    '''
    Used with the MicroScheduler-class, raised when the step counter is
    incremented above the configured value. The idea behind this is in order
    to detect when certain operations take longer to complete than what was
    expected.
    '''
    def __init__(self, limit, message):
        super().__init__(message)
        self.limit = limit
