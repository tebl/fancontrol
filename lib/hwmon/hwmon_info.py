import os
from ..exceptions import ControlRuntimeError
from ..utils import format_pwm, format_rpm, format_celsius
from ..control import BaseControl
from .hwmon_provider import HwmonProvider
from .hwmon_object import HwmonObject


class HwmonInfo(HwmonProvider):
    BASE_PATH = '/sys/class/hwmon'
    PREFIX = 'hwmon'


    def __init__(self, name, base_path):
        super().__init__(name)
        self.base_path = base_path
        self.load_keys()


    def load_keys(self):
        self.clear_entries()
        for dirpath, dirnames, filenames in os.walk(self.base_path):
            filenames.sort()
            for file in filenames:
                HwmonFile.try_importing(self, file, self.base_path)
            break


    def get_driver_name(self):
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


    def get_path(self):
        return os.path.join(
            self.BASE_PATH, 
            self.name
        )


    def suggest_key(self):
        '''
        Suggest configuration key for use with PromptBuilder, this should used
        as a value for start_at as we can't guarantee that a key isn't already
        used. Entries requiring more than one digit will start at 'a' instead. 
        '''
        if self.name[:-1] == 'hwmon':
            return self.name[-1:]
        return 'a'


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


    @classmethod
    def is_supported(cls):
        return os.path.isdir(cls.BASE_PATH)


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
    def try_parsing_hwmon(cls, value, dev_base):
        '''
        Parse hwnon path, passed either as a full path or as a relative path
        assumed to be located within dev_base.
        '''
        if not dev_base.startswith(cls.BASE_PATH):
            dev_base = os.path.join(cls.BASE_PATH, dev_base)
        if value.startswith(cls.BASE_PATH):
            return value
        print('failed for:', value)
        return None


    @classmethod
    def try_parsing_value(cls, value, dev_base):
        '''
        Parse hwnon entry paths, passed either as a full path or as a relative
        assumed to be located within dev_base.
        '''
        if not dev_base.startswith(cls.BASE_PATH):
            dev_base = os.path.join(cls.BASE_PATH, dev_base)

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
    def value_exists_for(cls, hwmon_name, hwmon_entry):
        if cls.is_supported() and hwmon_name.startswith(cls.PREFIX):
            return HwmonFile.value_exists_for(cls, hwmon_name, hwmon_entry)
        return None


class HwmonFile(HwmonObject):
    def __init__(self, hwmon_provider, name, base_path, input):
        self.hwmon_provider = hwmon_provider
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
        if self.hwmon_provider.matches(dev_base):
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
        if not self.hwmon_provider.matches(hwmon_name):
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


    @classmethod
    def try_importing(cls, hwmon_instance, file, base_path):
        for hwmon_class in cls.__subclasses__():
            if hwmon_class.try_importing(hwmon_instance, file, base_path):
                break


    @classmethod
    def value_exists_for(cls, base_class, hwmon_name, hwmon_entry):
        path = os.path.join(base_class.BASE_PATH, hwmon_name, hwmon_entry)
        return os.path.isfile(path)
                   

class HwmonTemp(HwmonFile):
    PREFIX = 'temp'
    SUFFIX = '_input'


    def format_value(self, value):
        value = int(value) / 1000
        return format_celsius(value)


    @classmethod
    def try_importing(cls, hwmon_instance, file, base_path):
        if file.startswith(cls.PREFIX) and file.endswith(cls.SUFFIX):
            o = cls(hwmon_instance, file[:-len(cls.SUFFIX)], base_path, file)
            hwmon_instance.register_sensor(o)


class HwmonFan(HwmonFile):
    PREFIX = 'fan'
    SUFFIX = '_input'


    def format_value(self, value):
        return format_rpm(int(value))


    @classmethod
    def try_importing(cls, hwmon_instance, file, base_path):
        if file.startswith(cls.PREFIX) and file.endswith(cls.SUFFIX):
            o = cls(hwmon_instance, file[:-len(cls.SUFFIX)], base_path, file)
            hwmon_instance.register_pwm_input(o)


class HwmonPWM(HwmonFile):
    PREFIX = 'pwm'
    SUFFIX = '_enable'


    def format_value(self, value):
        return format_pwm(int(value))


    def is_valid(self):
        return self.has_suffix_key() and self.has_suffix_key('_enable')


    @classmethod
    def try_importing(cls, hwmon_instance, file, base_path):
        if file.startswith(cls.PREFIX) and file.endswith(cls.SUFFIX):
            o = cls(hwmon_instance, file[:-len(cls.SUFFIX)], base_path, file[:-len(cls.SUFFIX)])
            hwmon_instance.register_device(o)
