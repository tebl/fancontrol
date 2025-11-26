import os, subprocess, time
from pprint import pprint
from ..exceptions import SensorException
from .hwmon_provider import HwmonProvider
from .hwmon_object import HwmonObject


class HwmonNvidia(HwmonProvider):
    BASE_PATH = '/virtual/nvidia'
    NVIDIA_SMI = '/usr/bin/nvidia-smi'
    PREFIX = 'nvidia'



    def __init__(self, name, gpu_id, gpu_description):
        super().__init__(name)
        self.gpu_id = gpu_id
        self.gpu_description = gpu_description
        self.load_keys()


    def get_driver_name(self):
        return self.gpu_description


    def get_path(self):
        return os.path.join(
            self.BASE_PATH, 
            'nvidia{}'.format(self.gpu_id)
        )


    def load_keys(self):
        self.clear_entries()
        self.register_sensor(NvidiaTemp(self, 'temp0'))
        self.register_pwm_input(NvidiaFan(self, 'fan0'))


    def suggest_key(self):
        '''
        As we're using numbers for hwmon-entries from sysfs, we'll put these
        somewhere from 'a' and up. This is only a suggestion that may or may
        not be discarded by the UI.
        '''
        return chr(ord('a') + self.gpu_id)


    @classmethod
    def is_supported(cls):
        return os.path.isfile(cls.NVIDIA_SMI)


    @classmethod
    def load_instances(cls, validation_func=None):
        '''
        Load instances by parsing the output from 'nvidia-smi -L', on my system
        this gives the following output:
            GPU 0: NVIDIA GeForce RTX 3050 (UUID: GPU-170050b3-0b6f-358f-2aed-9d00e32672b7)
        
        This should result in a new instance with "nvidia0" as name, 0 is also
        passed as gpu_id. Description is set to "NVIDIA GeForce RTX 3050".
        '''
        prefix = 'GPU '
        hwmon_list = []
        try:
            output = cls.run_command('-L')
            for line in output.split('\n'):
                if not line.startswith(prefix):
                    continue
                index = line.index(':')
                gpu_id = int(line[len(prefix):index])

                line = line[(index+1):]
                index = line.index('(')
                gpu_description = line[:index].strip()

                name = '{}{}'.format(cls.PREFIX, gpu_id)
                hwmon_entry = cls(name, gpu_id, gpu_description)
                if validation_func is None or validation_func(hwmon_entry):
                    hwmon_list.append(hwmon_entry)
        except ValueError as e:
            raise SensorException('Command parsing error: ' + str(e))
        return hwmon_list


    @classmethod
    def run_command(cls, *args):
        parts = [ cls.NVIDIA_SMI ]
        parts += list(args)
        try:
            result = subprocess.run(parts, check=True, capture_output=True, encoding='utf-8')
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise SensorException(str(e))


    @classmethod
    def try_parsing_hwmon(cls, value, dev_base):
        '''
        Parse hwnon path, passed either as a full path or as a relative path
        assumed to be located within dev_base.
        '''
        if value.startswith(cls.BASE_PATH):
            return value
        return None


    @classmethod
    def try_parsing_value(cls, value, dev_base):
        '''
        Parse hwnon entry paths, as it can't be used as a device entry we
        safely ignore the passed value for dev_base.
        '''
        if value.startswith(cls.BASE_PATH):
            # Value is full path to a file
            parts = value.split(os.path.sep)
            return parts[-2], parts[-1]
        return None


    @classmethod
    def value_exists_for(cls, hwmon_name, hwmon_entry):
        if hwmon_name.startswith(cls.PREFIX) and cls.is_supported():
            return hwmon_entry in ['temp0', 'fan0']
        return None


class NvidiaSensor(HwmonObject):
    REFRESH = 1
    FIELDS = [ 'temperature.gpu', 'fan.speed' ]
    last_data = {}
    last_updated = {}


    def __init__(self, hwmon_provider, name):
        super().__init__(hwmon_provider, name)


    def get_input(self, dev_base):
        if self.hwmon_provider.matches(dev_base):
            return self.name
        self.hwmon_provider.gpu_id
        return os.path.join(self.hwmon_provider.get_path(), self.name)


    def get_title(self, include_summary=False, include_value=True):
        if not include_summary:
            return self.name
        if not include_value:
            return self.name
        return '{} (value={})'.format(self.name, self.read_value())

    
    def is_valid(self):
        return True


    def get_field(self, field):
        data = self.__class__.get_data(self.hwmon_provider.gpu_id)
        return data[field]


    @classmethod
    def get_data(cls, gpu_id):
        if cls.should_refresh(gpu_id):
            output = HwmonNvidia.run_command(
                '--query-gpu={}'.format(','.join(cls.FIELDS)),
                '--format=csv,noheader,nounits', 
                '--id={}'.format(gpu_id)
            )
            for index, value in enumerate(output.split(',')):
                if gpu_id not in cls.last_data:
                    cls.last_data[gpu_id] = {}
                cls.last_data[gpu_id][cls.FIELDS[index]] = value.strip()
            cls.last_updated[gpu_id] = time.time()
        return cls.last_data[gpu_id]


    @classmethod
    def should_refresh(cls, gpu_id):
        if gpu_id not in cls.last_updated:
            return True
        if cls.last_updated[gpu_id] < (time.time() + cls.REFRESH):
            return True
        return False


    @classmethod
    def parse_command(cls):
        pass


class NvidiaTemp(NvidiaSensor):
    PREFIX = 'temp'

    def __init__(self, hwmon_provider, name):
        super().__init__(hwmon_provider, name)

    
    def read_value(self):
        return self.get_field('temperature.gpu')


class NvidiaFan(NvidiaSensor):
    PREFIX = 'fan'

    def __init__(self, hwmon_provider, name):
        super().__init__(hwmon_provider, name)

    
    def read_value(self):
        return self.get_field('fan.speed')
