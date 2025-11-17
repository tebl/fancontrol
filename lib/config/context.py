import os
from ..logger import LoggerMixin, Logger, InteractiveLogger, ConfirmPromptBuilder
from ..control import BaseControl
from ..hwmon_info import HwmonInfo
from ..logger import PromptBuilder

class InteractiveContext(LoggerMixin):
    SUBKEY_INDENT = '  '
    SUBKEY_CHILD =  '\u21B3 '
    UNIT_CELSIUS = '°C'

    CONFIRM_EXIT = False 

    def __init__(self, fan_config, parent):
        self.fan_config = fan_config
        self.parent = parent
        self.console = self.fan_config.console


    # def __getattribute__(self, name):
    #     match name:
    #         case 'console':
    #             return self.fan_config.console
    #     return super().__getattribute__(name)

    
    def interact(self):
        '''
        Nothing here, but that's only to be expected from a base class. The
        script will interact with contexts through a version of this method,
        returning a different context, or itself, that should become the new
        context from this point on.
        '''
        return self.parent
    

    def message(self, message='', styling=InteractiveLogger.DIRECT_REGULAR, end='\n'):
        self.console.log_direct(message, styling=styling, end=end)


    def error(self, message, styling=Logger.ERROR, end='\n'):
        self.message(message, styling=styling, end=end)


    def summarise(self, list, sep=': ', prefix=SUBKEY_INDENT):
        '''
        Used near the start of a context interaction to summarise common values
        used in this section. List should have the structure of (key, value)
        and the key is used so that we align all values on the screen.
        '''
        if not list:
            return
        self.message('Summary:', styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        key_pad = len(max([key for key, value, *params in list], key=len)) + len(sep)
        for key, value, *params in list:
            styling = Logger.DEBUG
            if params:
                styling = params.pop(0)
            self.message(prefix + self.format_key_value(key, value, key_pad=key_pad, sep=sep), styling=styling)
        self.message()


    def confirm_exit(self):
        '''
        Used to confirm exit if this feature has been enabled, if not we'll
        just return parent context. 
        '''
        if self.CONFIRM_EXIT:
            if self.console.prompt_choices(ConfirmPromptBuilder(self.console), prompt='Confirm exit') == 'y':
                return self.parent
            return self
        return self.parent


    def format_key_value(self, key, value, key_pad=16, sep=' '):
        if key_pad:
            return (key + sep).ljust(key_pad) + str(value)
        return (key + sep) + str(value)


    def format_pwm(self, value):
        return '({}/255)'.format(str(value).rjust(3))
    

    def format_temp(self, value):
        return str(value) + self.UNIT_CELSIUS


    def toggle_from_list(self, list, current, default):
        '''
        Used when stepping through possible values, one after another. Makes
        a copy so that we don't destroy anything valuable, but it will wrap
        around as needed.
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
        hwmon_list = []
        for dirpath, dirnames, filenames in os.walk(BaseControl.BASE_PATH):
            dirnames.sort()
            for dir in dirnames:
                hwmon_entry = HwmonInfo(dir, os.path.join(BaseControl.BASE_PATH, dir))
                if validation_func is None or validation_func(hwmon_entry):
                    hwmon_list.append(hwmon_entry)
            return hwmon_list


    def hwmon_list(self, hwmon_list):
        self.message('Listing hwmon:', styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        if hwmon_list:
            for entry in hwmon_list:
                self.message(self.SUBKEY_INDENT + entry.get_title(include_summary=True), styling=Logger.DEBUG)
        else:
            self.error(self.SUBKEY_INDENT + 'No suitable hwmon entries found. Has a suitable driver been loaded?')
        self.message()


    def hwmon_select(self, hwmon_list, current):
        choices = {}
        builder = PromptBuilder(self.console)
        builder.add_back()
        for hwmon_entry in hwmon_list:
            highlight = hwmon_entry.matches(current)
            key = builder.set_next(hwmon_entry.get_title(include_summary=False), start_at=hwmon_entry.suggest_key(), highlight=highlight)
            choices[key] = hwmon_entry
        
        selected = self.console.prompt_choices(builder, prompt='Select hwmon')
        match selected:
            case None | 'x':
                return None
            case _:
                return choices[selected]
        return None


    def hwmon_list_entries(self, hwmon_entries, current_value, is_current_hwmon=False):
        self.message('Listing entries:', styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        if hwmon_entries:
            for entry in hwmon_entries:
                styling = InteractiveLogger.DIRECT_HIGHLIGHT if is_current_hwmon and entry.matches(current_value) else Logger.DEBUG
                self.message(self.SUBKEY_INDENT + entry.get_title(include_summary=True), styling=styling)
        else:
            self.error(self.SUBKEY_INDENT + 'No suitable hwmon entries found. Has a suitable driver been loaded?')
        self.message()


    def hwmon_select_entry(self, hwmon_info, hwmon_entries, current_hwmon, current_entry, prompt='Select'):
        is_current_hwmon = hwmon_info.matches(current_hwmon)
        self.hwmon_list_entries(hwmon_entries, current_entry, is_current_hwmon)

        choices = {}
        builder = PromptBuilder(self.console)
        builder.add_back()
        for entry in hwmon_entries:
            highlight = True if is_current_hwmon and entry.matches(current_entry) else False
            key = builder.set_next(entry.get_title(include_summary=False), highlight=highlight)
            choices[key] = entry

        selected = self.console.prompt_choices(builder, prompt=prompt)
        match selected:
            case None | 'x':
                return None
            case _:
                return choices[selected]
        return None


    def __str__(self):
        suffix = 'Context'
        name = self.__class__.__name__
        if name.endswith(suffix):
            name = name[:-len(suffix)]
        return name