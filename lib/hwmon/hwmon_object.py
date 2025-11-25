from abc import ABC, abstractmethod


class HwmonObject(ABC):
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


    @abstractmethod
    def get_title(self, include_summary=False, include_value=True):
        ...


    @abstractmethod
    def is_valid(self):
        ...


    def matches(self, hwmon_name, name):
        if not self.hwmon_provider.matches(hwmon_name):
            return False
        return self.input == name


    @abstractmethod
    def read_value(self):
        ...


    @abstractmethod
    def suggest_key(self):
        '''
        Suggest configuration key for use with PromptBuilder, this should used
        as a value for start_at as we can't guarantee that a key isn't already
        used.
        '''
        ...
