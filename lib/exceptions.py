from .utils import to_keypair_str


class ControlException(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class ConfigurationError(ControlException):
    def __init__(self, message, details = None):
        if details:
            super().__init__(to_keypair_str(message, details))
        else:
            super().__init__(message)


class RuntimeError(ControlException):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


    def __str__(self):
        return '{}({})'.format(self.__class__.__name__, self.message)


class SensorException(RuntimeError):
    def __init__(self, message):
        super().__init__(message)