import os, string
from ..exceptions import *
from ..control import BaseControl
from ..logger import LoggerMixin, Logger, InteractiveLogger, PromptBuilder, ConfirmPromptBuilder
from .context import InteractiveContext
from ..hwmon_info import HwmonInfo


class HWMONContext(InteractiveContext):
    def __init__(self, *args):
        super().__init__(*args)
        self.hwmon = []


    def interact(self):
        self.summarise([
            ['Device', self.fan_config.settings.dev_base],
            [self.SUBKEY_CHILD + 'Path check', self.fan_config.settings.dev_path],
            [self.SUBKEY_CHILD + 'Driver check', self.fan_config.settings.dev_name]
        ])

        self.__load_hwmon()
        self.__list_hwmon()

        input = self.console.prompt_choices(self.__get_prompt_builder(), prompt=self)
        match input:
            case None | 'x':
                return self.parent
            case _:
                self.__change_hwmon(self.prompt_values[input])
                return self
        return self
    

    def __load_hwmon(self):
        self.hwmon = []
        for dirpath, dirnames, filenames in os.walk(BaseControl.BASE_PATH):
            dirnames.sort()
            for dir in dirnames:
                hwmon = HwmonInfo(dir, os.path.join(BaseControl.BASE_PATH, dir))
                if self.__is_suitable(hwmon):
                    self.hwmon.append(hwmon)
            break


    def __is_suitable(self, hwmon_entry):
        return hwmon_entry.devices and hwmon_entry.sensors and hwmon_entry.pwm_inputs


    def __list_hwmon(self):
        self.message('Listing hwmon:', styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        if self.hwmon:
            for entry in self.hwmon:
                self.message(self.SUBKEY_INDENT + entry.get_title(include_summary=True), styling=Logger.DEBUG)
        else:
            self.error(self.SUBKEY_INDENT + 'No suitable hwmon entries found. Has a suitable driver been loaded?')
        self.message()


    def __get_prompt_builder(self):
        builder = PromptBuilder(self.console, allowed_keystring=PromptBuilder.KEYSTRING_ALPHANUM)
        self.prompt_values = {}
        for entry in self.hwmon:
            key = builder.set_next(entry, highlight=entry.matches(self.fan_config.settings.dev_base), start_at=entry.suggest_key())
            self.prompt_values[key] = entry
        builder.add_back()
        return builder


    def __change_hwmon(self, hwmon_entry):
        self.message()
        self.message('Changing to {}:'.format(str(hwmon_entry)), styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        self.message(self.SUBKEY_CHILD + 'Fan configurations will be disabled.', styling=Logger.DEBUG, end='\n\n')
        if self.console.prompt_choices(ConfirmPromptBuilder(self.console), prompt='Confirm change') == 'y':
            self.fan_config.settings.set('Settings', 'dev_base', hwmon_entry.name)
            self.fan_config.settings.set('Settings', 'dev_name', hwmon_entry.get_dev_name())
            self.fan_config.settings.set('Settings', 'dev_path', hwmon_entry.get_dev_path())

            for section in self.fan_config.settings.sections():
                self.fan_config.settings.set_enabled(section, False)

            self.fan_config.settings.save()
            self.message('Configuration updated.', end='\n\n')


    def __str__(self):
        return 'hwmon'
    

class HWMONSelectedContext(InteractiveContext):
    def __init__(self, *args):
        super().__init__(*args)
        self.hwmon = []