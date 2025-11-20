import os, traceback
from ..logger import LoggerMixin, Logger, InteractiveLogger, ConfirmPromptBuilder, PromptValidationException
from ..control import BaseControl, Fan
from ..hwmon_info import HwmonInfo
from ..logger import PromptBuilder
from .. import utils


class Context(LoggerMixin):
    '''
    Base class, mostly here to define operations that don't require any kind of
    data as well as provide static building blocks for InteractiveContext.
    '''
    ACRONYMS = utils.ACRONYMS


    def __str__(self):
        suffix = 'Context'
        name = self.__class__.__name__
        if name.endswith(suffix):
            name = name[:-len(suffix)]
        return name


    @staticmethod
    def to_sentence(*args):
        return utils.to_sentence(*args, acronyms=__class__.ACRONYMS)


class InteractiveContext(Context):
    '''
    All contexts expected to function should inherit from InteractiveContext,
    implementing all common functionality such as looking up data or providing
    common interface functionality. 
    '''
    ACRONYMS = Context.ACRONYMS + ['PWM Input']

    ACTIONS = 'Actions available'
    CONFIG_UPDATED = 'Configuration updated.'

    CREATE = 'Create'
    CHANGE = 'Change'
    DELETE = 'Delete'
    CONFIRM = 'Confirm'
    SET = 'Set'
    EXIT = 'Exit'

    ENABLED = 'Enabled'
    DISABLED = 'Disabled'
    CONFIRM_CHANGE = Context.to_sentence(CONFIRM, CHANGE)

    START = 'Start'
    STOP = 'Stop'
    MINIMUM = 'Minimum'
    MIN = 'Min'
    MAXIMUM = 'Minimum'
    MAX = 'Max'

    NAME = 'Name'
    DEVICE = 'Device'
    DEVICE_MIN = Context.to_sentence(DEVICE, MIN)
    DEVICE_MAX = Context.to_sentence(DEVICE, MAX)
    DEVICE_START = Context.to_sentence(DEVICE, START)
    DEVICE_STOP = Context.to_sentence(DEVICE, STOP)
    SENSOR = 'Sensor'
    SENSOR_MIN = Context.to_sentence(SENSOR, MIN)
    SENSOR_MAX = Context.to_sentence(SENSOR, MAX)
    PWM_INPUT = 'PWM Input'
    STATUS = 'Status'

    SUBKEY_INDENT = '  '
    SUBKEY_CHILD =  '\u21B3 '

    CONFIRM_EXIT = False 

    def __init__(self, fan_config, parent):
        self.fan_config = fan_config
        self.parent = parent
        self.section = self.fan_config.settings.SETTINGS
        self.console = self.fan_config.console


    # def __getattribute__(self, name):
    #     match name:
    #         case 'console':
    #             return self.fan_config.console
    #     return super().__getattribute__(name)

    
    def interact(self, auto_select=None):
        '''
        Nothing here, but that's only to be expected from a base class. The
        script will interact with contexts through a version of this method,
        returning a different context, or itself, that should become the new
        context from this point on.
        '''
        return self.parent
    

    def message(self, message='', styling=InteractiveLogger.DIRECT_REGULAR, end='\n'):
        self.console.log_direct(message, styling=styling, end=end)
    @staticmethod
    def format_delay(value):
        return 'Controller updates every {} seconds'.format(value)

    def error(self, message, styling=Logger.ERROR, end='\n'):
        self.message(message, styling=styling, end=end)


    def summary(self, items=None, sep=': ', prefix=SUBKEY_INDENT):
        '''
        Used near the start of a context interaction to summarise common values
        used in this section. List should have the structure of (key, value)
        and the key is used so that we align all values on the screen. An optional
        third value can also be included to set formatter styling.
        '''
        if not items:
            return
        self.message('Summary:', styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        key_pad = len(max([key for key, value, *params in items], key=len)) + len(sep)
        value_pad = len(max([value for key, value, *params in items], key=len)) + len(sep)
        value_pad = utils.pad_number(value_pad)

        for key, value, *params in items:
            styling, key_legend = self.__summarise_params(params)
            
            if key_legend:
                self.message(prefix + self.__format_summary_entry(key, value, key_pad=key_pad, value_pad=value_pad, sep=sep), styling=styling, end='')
                self.message(key_legend, styling=InteractiveLogger.DIRECT_OPTION)
            else:
                self.message(prefix + self.__format_summary_entry(key, value, key_pad=key_pad, value_pad=value_pad, sep=sep), styling=styling)
        self.message()


    def add_summary_value(self, summary, title, value, format_func=None, validation_func=None, format_dict=None, error=None, extended=True):
        '''
        Add summary item to the summary, will be formatted using optional
        function if one has been supplied.
        
        Value validation can be performed in the same manner, but note that
        most of the supplied validation routines will provide values in their
        expected data formats. Such routines by default will be run in their
        extended versions.
        '''
        if not format_dict:
            format_dict = {}

        try:
            if validation_func:
                value = validation_func(value, extended=extended)
            if format_func:
                value = format_func(value)
        except PromptValidationException as e:
            error = str(e)

        if error:
            format_dict['styling'] = Logger.ERROR
        summary.append([title, value, format_dict])
        if error:
            summary.append([self.SUBKEY_INDENT + self.SUBKEY_CHILD + 'ERROR', error, { 'styling': InteractiveLogger.DIRECT_HIGHLIGHT }])
    

    def add_summary_config(self, summary, title, config_key, format_func=None, validation_func=None, format_dict=None, error=None):
        '''
        Add summary item that should be read from the configuration.
        '''
        value = self.fan_config.settings.get(self.section, config_key)
        self.add_summary_value(summary, title, value, format_func=format_func, validation_func=validation_func, format_dict=format_dict, error=error)


    def validate_number(self, value, extended=True):
        try:
            value = int(value)
        except ValueError:
            raise PromptValidationException('not a number')
        return value
    

    def validate_temp(self, value, extended=True):
        value = self.validate_number(value, True)
        if value < Fan.SENSOR_MIN:
            raise PromptValidationException('less than ' + str(Fan.SENSOR_MIN))
        return value


    def validate_pwm(self, value, extended=True):
        value = self.validate_number(value, True)
        if extended:
            if value < Fan.PWM_MIN:
                raise PromptValidationException('less than ' + str(Fan.PWM_MIN))
            if value > Fan.PWM_MAX:
                raise PromptValidationException('greater than ' + str(Fan.PWM_MAX))
        return value


    def validate_string(self, value, extended=True):
        if not value:
            raise PromptValidationException('empty value')
        return value


    def validate_hwmon(self, value, extended=True):
        hwmon_path = os.path.join(BaseControl.BASE_PATH, value)
        if not os.path.isdir(hwmon_path):
            raise PromptValidationException('hwmon not found')
        return value


    def validate_exists(self, value, extended=True):
        if value is None:
            raise PromptValidationException('doesn\'t have a value')
        return value


    def __summarise_params(self, params):
        if (len(params) > 1):
            raise ValueError('extra parameters encountered')
        styling = Logger.DEBUG
        key_legend = None
        if params:
            params = params.pop(0)
            if 'styling' in params:
                styling = params['styling']
            if 'key' in params:
                key_legend = params['key']
        return styling, key_legend


    def __format_summary_entry(self, key, value, key_pad=16, value_pad=0, sep=' '):
        if key_pad:
            return (key + sep).ljust(key_pad) + str(value).ljust(value_pad)
        return (key + sep) + str(value)


    def confirm_exit(self):
        '''
        Used to confirm exit if this feature has been enabled, if not we'll
        just return parent context. 
        '''
        if self.CONFIRM_EXIT:
            if self.console.prompt_choices(ConfirmPromptBuilder(self.console), prompt=self.to_sentence(self.CONFIRM, self.EXIT)) == 'y':
                return self.parent
            return self
        return self.parent


    def toggle_from_list(self, list, current, default):
        '''
        Used when stepping through possible values, one after another. Makes
        a copy so that we don't destroy anything valuable. Wraps around as
        needed.
        '''
        methods = list.copy()
        try:
            methods.append(methods[0])
            index = methods.index(current)
            return methods[index + 1]
        except ValueError:
            return default


    def expain_setting(self, name, value, description):
        '''
        Used to standardise how a setting explanation is printed. Nothing too
        exciting going on except for the fact that we're assuming that this is
        mainly for debugging.
        '''
        self.message('{} set to {}'.format(name, value))
        self.message(description.format(name, value), styling=Logger.DEBUG, end='\n\n')


    def hwmon_load(self, validation_func=None):
        '''
        Index sysfs for registered hwmon-entries, results are returned as a
        list of HwmonInfo instances. An optional validation method can be
        supplied in order to make decisions on which entries to include.
        '''
        hwmon_list = []
        for dirpath, dirnames, filenames in os.walk(BaseControl.BASE_PATH):
            dirnames.sort()
            for dir in dirnames:
                hwmon_entry = HwmonInfo(dir, os.path.join(BaseControl.BASE_PATH, dir))
                if validation_func is None or validation_func(hwmon_entry):
                    hwmon_list.append(hwmon_entry)
            return hwmon_list


    def hwmon_list(self, hwmon_list, current):
        '''
        List instances of HwmonInfo, a suitable list can be loaded using
        hwmon_load-method.
        '''
        self.message('Listing hwmon:', styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        if hwmon_list:
            for hwmon in hwmon_list:
                styling = InteractiveLogger.DIRECT_HIGHLIGHT if hwmon.matches(current) else Logger.DEBUG
                self.message(self.SUBKEY_INDENT + hwmon.get_title(include_summary=True), styling=styling)
        else:
            self.error(self.SUBKEY_INDENT + 'No suitable hwmon entries found. Has a suitable driver been loaded?')
        self.message()


    def hwmon_select(self, hwmon_list, current):
        '''
        Prompt the user to select an instance of HwmonInfo, a suitable list can
        be loaded using hwmon_load-method.
        '''
        choices = {}
        builder = PromptBuilder(self.console)
        builder.add_cancel()
        for hwmon in hwmon_list:
            is_current = hwmon.matches(current)
            key = builder.set_next(hwmon.get_title(include_summary=False), start_at=hwmon.suggest_key(), highlight=is_current)
            choices[key] = hwmon
            if is_current:
                builder.set_default(key)

        # Automatically use first choice as default if we don't have any other
        # options. This means that we can just hit ENTER and be done with it.
        if len(choices) == 1 and builder.get_default() is None:
            first_key = next(iter(choices.keys()))
            builder.set_default(first_key)

        selected = self.console.prompt_choices(builder, prompt='Select hwmon')
        match selected:
            case None | 'x':
                return None
            case _:
                return choices[selected]
        return None


    def hwmon_list_entries(self, hwmon_entries, current_hwmon, current_value):
        self.message('Listing entries:', styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        if hwmon_entries:
            for entry in hwmon_entries:
                styling = InteractiveLogger.DIRECT_HIGHLIGHT if entry.matches(current_hwmon, current_value) else Logger.DEBUG
                self.message(self.SUBKEY_INDENT + entry.get_title(include_summary=True), styling=styling)
        else:
            self.error(self.SUBKEY_INDENT + 'No suitable hwmon entries found. Has a suitable driver been loaded?')
        self.message()


    def hwmon_select_entry(self, hwmon_entries, current_hwmon, current_entry, prompt='Select resource'):
        self.hwmon_list_entries(hwmon_entries, current_hwmon, current_entry)

        choices = {}
        builder = PromptBuilder(self.console)
        builder.add_cancel()
        for entry in hwmon_entries:
            is_current = True if entry.matches(current_hwmon, current_entry) else False
            key = builder.set_next(entry.get_title(include_summary=False), start_at=entry.suggest_key(), highlight=is_current)
            choices[key] = entry
            if is_current:
                builder.set_default(key)

        # Automatically use first choice as default if we don't have any other
        # options. This means that we can just hit ENTER and be done with it.
        if len(choices) == 1 and builder.get_default() is None:
            first_key = next(iter(choices.keys()))
            builder.set_default(first_key)

        selected = self.console.prompt_choices(builder, prompt=prompt)
        match selected:
            case None | 'x':
                return None
            case _:
                return choices[selected]
        return None


    def print_configuration_error(self, exception):
        self.error('Configuration error: ' + str(exception))
        if self.fan_config.dev_debug:
            error_str = traceback.format_exc()
            self.message(error_str, styling=Logger.DEBUG)
        self.message()


    @staticmethod
    def format_delay(value):
        return 'Controller updates every {} seconds'.format(value)