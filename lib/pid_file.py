import os
from .exceptions import ControlRuntimeError
from .logger import LoggerMixin


class PIDFile(LoggerMixin):
    '''
    Takes care of writing, and then finally unlinking the pid-file used by the
    program.
    '''

    def __init__(self, logger, pid_path, zap_if_exists=False):
        self.logger = logger
        self.pid_path = pid_path
        self.zap_if_exists = zap_if_exists
        self.value = os.getpid()
        self.created = False


    def get(self):
        return self.value

    
    def create(self):
        if os.path.isfile(self.pid_path) and not self.zap_if_exists:
            raise ControlRuntimeError('{} pid already exists'.format(self))

        try:
            with open(self.pid_path, 'w') as file:
                file.write(str(self.value))
            self.created = True
            self.log_verbose('{} created'.format(self))
        except PermissionError as e:
            raise ControlRuntimeError('{} could not write pid ({})'.format(self, str(e)))
        return self
    

    def unlink(self):
        if self.created and os.path.isfile(self.pid_path):
            os.remove(self.pid_path)
            self.log_verbose('{} removed'.format(self))
        return True
    

    def __enter__(self):
        self.create()


    def __exit__(self, exc_type, exc_value, traceback):
        self.unlink()


    def __str__(self):
        return '{}({})'.format(self.__class__.__name__, self.pid_path)
