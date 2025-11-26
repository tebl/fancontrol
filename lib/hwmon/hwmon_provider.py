import os
from abc import ABC, abstractmethod
from .hwmon_object import HwmonObject


class HwmonProvider(ABC):
    instances = []
    instances_loaded = False
    logger = None
    settings = None
    

    def __init__(self, name):
        self.name = name
        self.clear_entries()


    def clear_entries(self):
        self.devices = []
        self.sensors = []
        self.pwm_inputs = []


    @abstractmethod
    def get_driver_name(self):
        '''
        Used by the routines in order to verify that hwmon-entries haven't been
        renumbered between boots.
        '''
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
        '''
        Get base path for driver entries, and while it takes the format of a
        Posix-compatible path - it just requires that entries without remains
        unique.
        '''
        ...


    @abstractmethod
    def load_entries(self):
        '''
        Load objects associated with the entry. While this is explicitly called
        during instantiation it's conceivable that we at some point need to
        call it again in order to reload data.
        '''
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
        '''
        Determine if the the provider is supported on this system, should
        return False if some dependecy is missing.
        '''
        ...


    @classmethod
    def parse_hwmon(cls, value, dev_base):
        for provider_type in cls.__subclasses__():
            result = provider_type.try_parsing_hwmon(value, dev_base)
            if result is not None:
                return result
        return None


    @classmethod
    def parse_value(cls, value, dev_base):
        for provider_type in cls.__subclasses__():
            result = provider_type.try_parsing_value(value, dev_base)
            if result is not None:
                return result
        return None


    @classmethod
    @abstractmethod
    def try_parsing_hwmon(cls, value, dev_base):
        '''
        Parse hwnon path, passed either as a full path or as a relative path
        assumed to be located within dev_base.
        '''
        ...


    @classmethod
    @abstractmethod
    def try_parsing_value(cls, value, dev_base):
        '''
        Parse hwnon entry paths, passed either as a full path or as a relative
        path assumed to be located within dev_base.
        '''
        ...
    

    @classmethod
    def configure(cls, settings, logger):
        cls.settings = settings
        cls.logger = logger


    @classmethod
    def load(cls):
        '''
        Load provider instances using supported sub-systems, as determined by the
        implementation itself. Settings and logger provided by the system in case
        I ever need them.
        '''
        cls.instances.clear()
        for provider_type in cls.__subclasses__():
            if provider_type.is_supported():
                cls.instances += provider_type.load_provider()
        cls.instances_loaded = True
        return cls.instances_loaded


    @classmethod
    @abstractmethod
    def filter_instances(cls, filter_func=None):
        '''
        Filter loaded instances, either getting all of them or by providing a
        filter function you can choose to evaluate them one by one. Note that
        while this implementation is tagged as @abstractmethod, this is to
        enforce the inclusion of an implementation in child-classes - the
        implementation of which would usually include a call to
        get_provider_filter.
        '''
        if not cls.instances_loaded:
            cls.load()
        results = []
        for provider_instance in cls.instances:
            if filter_func is None or filter_func(provider_instance):
                results.append(provider_instance)
        return results


    @classmethod
    def get_provider_filter(cls, orig_filter_func=None):
        '''
        Intended to be called from a child class in order to create a filter
        function that will both constrain the class type as well as use the
        provided caller-defined function. If called from the parent we just
        return whatever is provided to it.

        This enables us to do things such as HwmonNvidia.filter_instances()
        to get only instances of HwmonNvidia while
        HwmonProvider.filter_instances() would return instances regardless of
        implementation.
        '''
        if cls is HwmonProvider:
            return orig_filter_func
        def filter_subtype(hwmon_provider):
            if type(hwmon_provider) is cls:
                if orig_filter_func is None:
                    return True
                return orig_filter_func(hwmon_provider)
            return False
        return filter_subtype


    @classmethod
    @abstractmethod
    def load_provider(cls):
        '''
        Load instances from a specific provider.
        '''
        ...


    @classmethod
    def value_exists(cls, hwmon_name, hwmon_entry):
        '''
        Check that information obtained using parse_value actually exists,
        the implementation of which is left up to the provider instance
        itself.
        '''
        for provider_type in cls.__subclasses__():
            result = provider_type.value_exists_for(hwmon_name, hwmon_entry)
            if result is not None:
                return result
        return False


    @classmethod
    @abstractmethod
    def value_exists_for(cls, hwmon_name, hwmon_entry):
        ...