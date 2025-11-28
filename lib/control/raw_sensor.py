import os.path
from ..logger import LoggerMixin
from ..exceptions import SensorException, ConfigurationError


class RawSensor(LoggerMixin):
    def __init__(self, logger, name, hwmon_object, auto_load=True):
        self.logger = logger
        self.name = name
        self.hwmon_object = hwmon_object


    def format_value(self, value):
        '''
        Format the specified value for display as text, potentially adding more
        sensible details in a subclass.
        '''
        return str(value)
    

    def get_title(self, include_summary=False):
        if not include_summary:
            return self.name
        return '{} (value={})'.format(
            self.name,
            str(self.format_value(self.read_value()))
        )


    def get_value(self):
        '''
        Returns the last read sensor value
        '''
        return self.value


    def get_value_str(self):
        '''
        Returns the last read sensor value as a string, formatted using
        format_value_str.
        '''
        return self.format_value(self.get_value())
    

    def load_configuration(self):
        if not self.hwmon_object:
            raise ConfigurationError('{}.{} not found'.format(self, 'device'), self.hwmon_object)
        if not self.hwmon_object.is_valid():
            raise ConfigurationError('{}.{} not valid'.format(self, 'device'), self.hwmon_object)
        self.log_verbose('{}.{} input OK'.format(self, 'device', self.hwmon_object))
        return True


    def read_value(self):
        return self.hwmon_object.read_value()


    def require_writable(self):
        return False
    

    def require_has_enable(self):
        return False


    def write_value(self, value, ignore_exceptions=False):
        return self.hwmon_object.write_value(value, ignore_exceptions)


    def update(self):
        '''
        Update sensor value, intended to be called at regular intervals. Note
        that this is the only point where values are actually updated, other
        methods work with stored values.
        '''
        self.value = self.read_value()
        self.log_verbose('{} = {}'.format(self, self.get_value_str()))


    def __str__(self):
        return '{}({})'.format(self.__class__.__name__, self.name)