import os.path
from ..logger import LoggerMixin
from ..exceptions import SensorException, ConfigurationError


class RawSensor(LoggerMixin):
    def __init__(self, logger, name, device_path, auto_load=True):
        self.logger = logger
        self.name = name
        self.device_path = device_path


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
            str(self.format_value(self.read_int(self.device_path)))
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
        if not os.path.isfile(self.device_path):
            raise ConfigurationError('{}.{} not found'.format(self, 'device_path'), self.device_path)
        if not os.access(self.device_path, os.R_OK):
            raise ConfigurationError('{}.{} read access missing'.format(self, 'device_path'), self.device_path)
        self.log_verbose('{}.{} input OK'.format(self, 'device_path', self.device_path))
        return True


    def read(self, sensor_path):
        '''
        Reads the value of a specified sensor, and while this might be caused
        by various errors we're simplifying all of them since the bottom is
        that we didn't get the data needed.
        '''
        try:
            with open(sensor_path, 'r') as file:
                data = file.read()
                return int(data)
        except FileNotFoundError as e:
            raise SensorException(str(e))


    def read_int(self, sensor_path):
        '''
        Reads an integer value from the specified sensor, and while this might
        be caused by various errors we're simplifying all of them since the
        bottom is that we didn't get the data needed.
        '''
        try:
            return int(self.read(sensor_path))
        except ValueError as e:
            raise SensorException(str(e))


    def update(self):
        '''
        Update sensor value, intended to be called at regular intervals. Note
        that this is the only point where values are actually updated, other
        methods work with stored values.
        '''
        self.value = self.read_int(self.device_path)
        self.log_verbose('{} = {}'.format(self, self.get_value_str()))


    def write(self, sensor_path, value):
        '''
        Write data to the specified sensor, will raise SensorException if that
        fails in some way. Note that since we're working with sysfs we probably
        shouldn't write anything that doesn't look like an int, but checking is
        people who know what they're doing.
        '''
        try:
            with open(sensor_path, 'w') as file:
                file.write('{}'.format(str(value)))
                return True
        except (FileNotFoundError, PermissionError) as e:
            raise SensorException('{} could not write {} to {} ({})'.format(self, str(value), sensor_path, e))
        return False


    def __str__(self):
        return '{}({})'.format(self.__class__.__name__, self.name)