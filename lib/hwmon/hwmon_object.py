from abc import ABC, abstractmethod
from ..exceptions import SensorException


class HwmonObject(ABC):
    PREFIX = None


    def __init__(self, hwmon_provider, name):
        self.hwmon_provider = hwmon_provider
        self.name = name


    @abstractmethod
    def get_input(self, dev_base):
        '''
        Get input path if the supplied dev_base does not match the one we
        retrieved the input from. Note that dev_base is a partial name such
        as 'hwmon4', and will most likely not be a complete path.
        '''
        ...

    
    def get_symbol_name(self):
        '''
        Should return a string that uniquely identifies this object, used
        internally and will in no way be consistent outside of this software.
        '''
        return '{}::{}'.format(str(self.hwmon_provider), self.name)


    def get_provider(self):
        return self.hwmon_provider


    @abstractmethod
    def get_title(self, include_summary=False, include_value=True, symbolic_name=True):
        ...


    @abstractmethod
    def is_valid(self):
        ...
    

    def has_enable(self):
        return False
    

    @abstractmethod
    def is_writable(self):
        return False


    @abstractmethod
    def matches(self, hwmon_entry):
        ...


    @abstractmethod
    def read_value(self):
        ...


    @abstractmethod
    def read_formatted(self):
        ...


    def suggest_key(self):
        '''
        Suggest configuration key for use with PromptBuilder, this should used
        as a value for start_at as we can't guarantee that a key isn't already
        used.
        '''
        prefix = self.__class__.PREFIX
        if prefix is not None and self.name.startswith(prefix):
            number = self.name[len(prefix):]
            try:
                number = int(number)
                if number <= 9:
                    return str(number)
                return 'a'
            except ValueError:
                pass
        return None
