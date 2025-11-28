import os
from ..exceptions import ControlRuntimeError, SensorException
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
        self.load_entries()


    def load_entries(self):
        self.clear_entries()
        for dirpath, dirnames, filenames in os.walk(self.base_path):
            filenames.sort()
            for file in filenames:
                HwmonFile.try_importing(self, file, self.base_path)
            break


    def get_driver_name(self):
        file_path = os.path.join(self.base_path, 'name')
        return self.read_from(file_path, strip_contents=True)


    def get_driver_path(self, prefix='/sys/'):
        device_path = os.path.join(self.base_path, 'device')
        device_path = os.path.realpath(device_path)
        if not device_path[:len(prefix)] == prefix:
            raise ValueError(device_path)
        return device_path[len(prefix):]


    def get_path(self):
        return self.base_path


    def suggest_key(self):
        '''
        Suggest configuration key for use with PromptBuilder, this should used
        as a value for start_at as we can't guarantee that a key isn't already
        used. Entries requiring more than one digit will start at 'a' instead. 
        '''
        if self.name[:-1] == 'hwmon':
            return self.name[-1:]
        return 'a'
    

    @classmethod
    def filter_instances(cls, filter_func=None):
        return super().filter_instances(filter_func=cls.get_provider_filter(filter_func))


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
    def load_provider(cls):
        '''
        Index sysfs for registered hwmon-entries, results are returned as a
        list of HwmonInfo instances. An optional validation method can be
        supplied in order to make decisions on which entries to include.
        '''
        instances = []
        for dirpath, dirnames, filenames in os.walk(cls.BASE_PATH):
            dirnames.sort()
            for dir in dirnames:
                hwmon_entry = cls(dir, os.path.join(cls.BASE_PATH, dir))
                instances.append(hwmon_entry)
        return instances
    

    @classmethod
    def read_from(cls, file_path, strip_contents=True, convert_func=None):
        try:
            with open(file_path, 'r') as file:
                data = file.read()
                if strip_contents:
                    data = data.strip()
                if convert_func is not None:
                    data = convert_func(data)
                return data
        except (FileNotFoundError, ValueError) as e:
            raise SensorException(str(e))


    @classmethod
    def try_parsing_value(cls, value, dev_base):
        '''
        Parse hwnon entry paths, passed either as a full path or as a relative
        assumed to be located within dev_base.
        '''
        if isinstance(dev_base, HwmonProvider):
            dev_base = dev_base.get_path()

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


    @classmethod
    def write_to(cls, file_path, value, convert_func=str):
        if convert_func is not None:
            value = convert_func(value)

        try:
            with open(file_path, 'w') as file:
                file.write('{}'.format(str(value)))
                return True
        except (FileNotFoundError, PermissionError) as e:
            raise SensorException('{} could not write {} to {} ({})'.format(cls, str(value), file_path, e))
        return False


class HwmonFile(HwmonObject):
    def __init__(self, hwmon_provider, name, base_path, input):
        self.hwmon_provider = hwmon_provider
        self.name = name
        self.base_path = base_path
        self.input = input
        self.label = self.read_key('_label')


    def get_input(self, dev_base):
        '''
        Get input path if the supplied dev_base does not match the one we
        retrieved the input from. Note that dev_base is a partial name such
        as 'hwmon4', and will most likely not be a complete path.
        '''
        if self.hwmon_provider.matches(dev_base):
            return self.input
        return os.path.join(self.base_path, self.input)


    def get_title(self, include_summary=False, include_value=True, symbolic_name=True):
        name = self.input
        if symbolic_name:
            name = self.get_symbol_name()

        terms = []
        if include_summary:
            if include_value:
                terms.append('value={}'.format(self.read_formatted()))
            if self.label:
                terms.append('label={}'.format(self.label))
        if terms:
            return '{} ({})'.format(name, ', '.join(terms))
        return name


    def has_suffix_key(self, suffix=''):
        file_path = self.get_entry_path(suffix)
        return os.path.isfile(file_path)


    def is_valid(self):
        file_path = self.get_entry_path('_input')
        if not os.path.isfile(file_path):
            raise ControlRuntimeError('path {} did not exist'.format(file_path))
        if not os.access(file_path, os.R_OK):
            raise ControlRuntimeError('path {} is not readable'.format(file_path))
        return True


    def is_writable(self):
        return True


    def matches(self, hwmon_entry):
        return self.input == hwmon_entry


    def read_key(self, suffix=''):
        file_path = self.get_entry_path(suffix)
        if os.path.isfile(file_path):
            try:
                return HwmonInfo.read_from(file_path, strip_contents=True)
            except SensorException as e:
                pass
        return None


    def read_formatted(self):
        return str(self.read_value())


    def read_value(self):
        return HwmonInfo.read_from(
            os.path.join(self.base_path, self.input),
            strip_contents=True, 
            convert_func=int
        )


    def write_value(self, value, ignore_exceptions=False):
        try:
            return HwmonInfo.write_to(os.path.join(self.base_path, self.input), value)
        except SensorException as e:
            if not ignore_exceptions:
                raise
        return False


    def get_entry_path(self, suffix=''):
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


    def read_formatted(self):
        return format_celsius(self.read_value())


    def read_value(self):
        value = super().read_value()
        value = round(int(value) / 1000)
        return value


    @classmethod
    def try_importing(cls, hwmon_instance, file, base_path):
        if file.startswith(cls.PREFIX) and file.endswith(cls.SUFFIX):
            o = cls(hwmon_instance, file[:-len(cls.SUFFIX)], base_path, file)
            hwmon_instance.register_sensor(o)


class HwmonFan(HwmonFile):
    PREFIX = 'fan'
    SUFFIX = '_input'


    def read_formatted(self):
        return format_rpm(self.read_value())


    @classmethod
    def try_importing(cls, hwmon_instance, file, base_path):
        if file.startswith(cls.PREFIX) and file.endswith(cls.SUFFIX):
            o = cls(hwmon_instance, file[:-len(cls.SUFFIX)], base_path, file)
            hwmon_instance.register_pwm_input(o)


class HwmonPWM(HwmonFile):
    PREFIX = 'pwm'
    SUFFIX = '_enable'


    def read_formatted_value(self):
        return format_pwm(self.read_value())


    def has_enable(self):
        return True


    def is_valid(self):
        return self.has_suffix_key() and self.has_suffix_key(self.SUFFIX)


    def read_enable(self):
        return HwmonInfo.read_from(
            self.get_entry_path(self.SUFFIX),
            strip_contents=True, 
            convert_func=int
        )


    def write_enable(self, value, ignore_exceptions=False):
        try:
            return HwmonInfo.write_to(self.get_entry_path(self.SUFFIX), value)
        except ControlRuntimeError as e:
            if not ignore_exceptions:
                raise
        return False


    @classmethod
    def try_importing(cls, hwmon_instance, file, base_path):
        if file.startswith(cls.PREFIX) and file.endswith(cls.SUFFIX):
            o = cls(hwmon_instance, file[:-len(cls.SUFFIX)], base_path, file[:-len(cls.SUFFIX)])
            hwmon_instance.register_device(o)
