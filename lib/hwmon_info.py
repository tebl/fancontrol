import os
from abc import ABC, ABCMeta, abstractmethod
from .exceptions import ControlRuntimeError
from .utils import format_pwm, format_rpm, format_celsius
from .control import BaseControl


class HwmonProvider(ABC):
    def __init__(self, name):
        self.name = name
        self.devices = []
        self.sensors = []
        self.pwm_inputs = []


    @abstractmethod
    def get_dev_name(self):
        ...


    def get_title(self, include_summary=False):
        if not include_summary:
            return self.name
        return '{} (driver={}, devices={}, sensors={}, pwm_inputs={})'.format(
            self.name, 
            self.get_dev_name(),
            len(self.devices),
            len(self.sensors),
            len(self.pwm_inputs)
        )


    @abstractmethod
    def load_keys(self):
        ...


    def matches(self, name):
        return self.name == name


    @abstractmethod
    def register(self, hwmon_object):
        ...


    @classmethod
    def load_instances(cls, validation_func=None):
        results = []
        results += HwmonInfo.load_instances(validation_func)
        return results


class HwmonInfo(HwmonProvider):
    BASE_PATH = '/sys/class/hwmon'


    def __init__(self, name, base_path):
        super().__init__(name)
        self.base_path = base_path
        self.load_keys()


    def load_keys(self):
        self.devices = []
        self.sensors = []
        self.pwm_inputs = []
        for dirpath, dirnames, filenames in os.walk(self.base_path):
            filenames.sort()
            for file in filenames:
                HwmonObject.try_importing(self, file, self.base_path)
            break


    def get_dev_name(self):
        file_path = os.path.join(self.base_path, 'name')
        try:
            with open(file_path, 'r') as file:
                data = file.read()
                return data.strip()
        except FileNotFoundError as e:
            raise ControlRuntimeError(str(e))


    def get_dev_path(self, prefix='/sys/'):
        device_path = os.path.join(self.base_path, 'device')
        device_path = os.path.realpath(device_path)
        if not device_path[:len(prefix)] == prefix:
            raise ValueError(device_path)
        return device_path[len(prefix):]


    def register(self, hwmon_object):
        if type(hwmon_object) is HwmonPWM:
            self.devices.append(hwmon_object)
        if type(hwmon_object) is HwmonTemp:
            self.sensors.append(hwmon_object)
        if type(hwmon_object) is HwmonFan:
            self.pwm_inputs.append(hwmon_object)


    def suggest_key(self):
        '''
        Suggest configuration key for use with PromptBuilder, this should used
        as a value for start_at as we can't guarantee that a key isn't already
        used. Entries requiring more than one digit will start at 'a' instead. 
        '''
        if self.name[:-1] == 'hwmon':
            return self.name[-1:]
        return 'a'


    def __str__(self):
        return self.get_title()
    

    @staticmethod
    def get_hwmon_from_value(value, dev_base):
        '''
        Get hwmon value from what's possibly the full path to a specific entry,
        if it doesn't start with the base path then we simply assume we're
        working with relative paths.
        '''
        if value.startswith(BaseControl.BASE_PATH):
            return value.split(os.path.sep)[-2]
        return dev_base
    

    @staticmethod
    def get_entry_from_value(value, dev_base):
        '''
        Same as get_hwmon_from_value except we only want entry name.
        '''
        if value.startswith(BaseControl.BASE_PATH):
            return value.split(os.path.sep)[-1]
        return value


    @staticmethod
    def read_contents(file_path, strip_contents=True, convert_func=None):
        try:
            with open(file_path, 'r') as file:
                data = file.read()
                if strip_contents:
                    data = data.strip()
                if convert_func is not None:
                    data = convert_func(data)
                return data
        except (FileNotFoundError, ValueError) as e:
            raise ControlRuntimeError(str(e))


    @classmethod
    def load_instances(cls, validation_func=None):
        '''
        Index sysfs for registered hwmon-entries, results are returned as a
        list of HwmonInfo instances. An optional validation method can be
        supplied in order to make decisions on which entries to include.
        '''
        hwmon_list = []
        for dirpath, dirnames, filenames in os.walk(cls.BASE_PATH):
            dirnames.sort()
            for dir in dirnames:
                hwmon_entry = cls(dir, os.path.join(cls.BASE_PATH, dir))
                if validation_func is None or validation_func(hwmon_entry):
                    hwmon_list.append(hwmon_entry)
            return hwmon_list


class HwmonObject:
    def __init__(self, hwmon_info, name, base_path, input):
        self.hwmon_info = hwmon_info
        self.name = name
        self.base_path = base_path
        self.input = input
        self.label = self.read_key('_label')


    def format_value(self, value):
        return str(value)


    def get_input(self, dev_base):
        '''
        Get input path if the supplied dev_base does not match the one we
        retrieved the input from. Note that dev_base is a partial name such
        as 'hwmon4', and will most likely not be a complete path.
        '''
        if self.hwmon_info.matches(dev_base):
            return self.input
        return os.path.join(self.base_path, self.input)


    def get_title(self, include_summary=False, include_value=True):
        terms = []
        if include_summary:
            if include_value:
                terms.append('value=' + self.read_value())
            if self.label:
                terms.append('label=' + self.label)
        if terms:
            return '{} ({})'.format(
                self.input,
                ', '.join(terms)
            )
        return self.input


    def is_valid(self):
        return self.has_suffix_key('_input')


    def matches(self, hwmon_name, name):
        if not self.hwmon_info.matches(hwmon_name):
            return False
        return self.input == name
    

    def read_key(self, suffix=''):
        file_path = self.__get_path(suffix)
        if os.path.isfile(file_path):
            try:
                return HwmonInfo.read_contents(file_path, strip_contents=True)
            except ControlRuntimeError as e:
                pass
        return None


    def read_value(self):
        return HwmonInfo.read_contents(
            os.path.join(self.base_path, self.input),
            strip_contents=True, 
            convert_func=self.format_value
        )
    

    def suggest_key(self):
        prefix = self.__class__.PREFIX
        if self.name.startswith(prefix):
            number = self.name[len(prefix):]
            try:
                number = int(number)
                if number <= 9:
                    return str(number)
                return 'a'
            except ValueError:
                pass
        return None


    def has_suffix_key(self, suffix=''):
        file_path = self.__get_path(suffix)
        return os.path.isfile(file_path)


    def __get_path(self, suffix=''):
        result = os.path.join(self.base_path, self.name)
        if not suffix:
            return result
        return result + suffix


    def __str__(self):
        return self.get_title(include_summary=True)


    @staticmethod
    def try_importing(hwmon_instance, file, base_path):
        for hwmon_class in [HwmonFan, HwmonPWM, HwmonTemp]:
            if hwmon_class.try_importing(hwmon_instance, file, base_path):
                break


class HwmonTemp(HwmonObject):
    PREFIX = 'temp'
    SUFFIX = '_input'


    def format_value(self, value):
        value = int(value) / 1000
        return format_celsius(value)


    @staticmethod
    def try_importing(hwmon_instance, file, base_path):
        if file.startswith(__class__.PREFIX) and file.endswith(__class__.SUFFIX):
            o = __class__(hwmon_instance, file[:-len(__class__.SUFFIX)], base_path, file)
            if o.is_valid():
                hwmon_instance.register(o)


class HwmonFan(HwmonObject):
    PREFIX = 'fan'
    SUFFIX = '_input'


    def format_value(self, value):
        return format_rpm(int(value))


    @staticmethod
    def try_importing(hwmon_instance, file, base_path):
        if file.startswith(__class__.PREFIX) and file.endswith(__class__.SUFFIX):
            o = __class__(hwmon_instance, file[:-len(__class__.SUFFIX)], base_path, file)
            if o.is_valid():
                hwmon_instance.register(o)


class HwmonPWM(HwmonObject):
    PREFIX = 'pwm'
    SUFFIX = '_enable'


    def format_value(self, value):
        return format_pwm(int(value))


    def is_valid(self):
        return self.has_suffix_key() and self.has_suffix_key('_enable')


    @staticmethod
    def try_importing(hwmon_instance, file, base_path):
        if file.startswith(__class__.PREFIX) and file.endswith(__class__.SUFFIX):
            o = __class__(hwmon_instance, file[:-len(__class__.SUFFIX)], base_path, file[:-len(__class__.SUFFIX)])
            if o.is_valid():
                hwmon_instance.register(o)
