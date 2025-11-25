import os
from abc import ABC, abstractmethod
from .hwmon_object import HwmonObject


class HwmonProvider(ABC):
    def __init__(self, name):
        self.name = name
        self.clear_entries()


    def clear_entries(self):
        self.devices = []
        self.sensors = []
        self.pwm_inputs = []


    @abstractmethod
    def get_driver_name(self):
        ...


    def get_title(self, include_summary=False):
        if not include_summary:
            return self.name
        return '{} (driver={}, devices={}, sensors={}, pwm_inputs={})'.format(
            self.name, 
            self.get_driver_name(),
            len(self.devices),
            len(self.sensors),
            len(self.pwm_inputs)
        )


    @abstractmethod
    def get_path(self):
        ...


    @abstractmethod
    def load_keys(self):
        ...


    def matches(self, name):
        return self.name == name
    

    def register_device(self, hwmon_object):
        if not isinstance(hwmon_object, HwmonObject):
            return
        if not hwmon_object.is_valid():
            return
        self.devices.append(hwmon_object)


    def register_sensor(self, hwmon_object):
        if not isinstance(hwmon_object, HwmonObject):
            return
        if not hwmon_object.is_valid():
            return
        self.sensors.append(hwmon_object)


    def register_pwm_input(self, hwmon_object):
        if not isinstance(hwmon_object, HwmonObject):
            return
        if not hwmon_object.is_valid():
            return
        self.pwm_inputs.append(hwmon_object)


    @abstractmethod
    def suggest_key(self):
        '''
        Suggest configuration key for use with PromptBuilder, this should used
        as a value for start_at as we can't guarantee that a key isn't already
        used.
        '''
        ...


    def __str__(self):
        return self.get_title()
    

    @classmethod
    @abstractmethod
    def is_supported(cls):
        ...


    @classmethod
    def parse_value(cls, value, dev_base):
        for provider_type in cls.__subclasses__():
            result = provider_type.try_parsing_value(value, dev_base)
            if result is not None:
                return result
        return None


    @classmethod
    def try_parsing_value(cls, value, dev_base):
        '''
        Parse hwnon entry paths, passed either as a full path or as a relative
        assumed to be located within dev_base.
        '''
        if value.startswith(cls.BASE_PATH):
            # Value is full path to a file
            parts = value.split(os.path.sep)
            return parts[-2], parts[-1]
        elif dev_base.startswith(cls.BASE_PATH):
            if not value.startswith(os.path.sep):
                # Value is relative to dev_base
                parts = dev_base.split(os.path.sep)
                return parts[-1], value
        return None
    

    @classmethod
    def load_instances(cls, validation_func=None):
        results = []
        for provider_type in cls.__subclasses__():
            if provider_type.is_supported():
                results += provider_type.load_instances(validation_func)
        return results