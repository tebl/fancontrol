import os, string
from ..exceptions import *
from ..control import BaseControl
from ..logger import LoggerMixin, Logger, InteractiveLogger, PromptBuilder
from .context import InteractiveContext
from .hwmon_info import HwmonInfo


class HWMONContext(InteractiveContext):
    def __init__(self, *args):
        super().__init__(*args)
        self.hwmon = []


    def interact(self):
        self.summarise([
            ['Device', self.fan_config.settings.dev_base],
            [self.SUBKEY_CHILD + 'Path check', self.fan_config.settings.dev_path],
            [self.SUBKEY_CHILD + 'Driver name check', self.fan_config.settings.dev_name]
        ])

        self.__load_hwmon()
        self.__list_hwmon()

        input = self.console.prompt_choices(self.__get_prompt_builder(), prompt=self)
        match input:
            case None | 'x':
                return self.parent
            case _:
                self.message('You entered ' + input)
                return self
        return self
    

    def __load_hwmon(self):
        self.hwmon = []
        for dirpath, dirnames, filenames in os.walk(BaseControl.BASE_PATH):
            dirnames.sort()
            for dir in dirnames:
                entry = HwmonInfo(dir, os.path.join(BaseControl.BASE_PATH, dir))
                if self.__hwmon_suitable(entry):
                    self.hwmon.append(entry)
            break


    def __hwmon_suitable(self, hwmon_entry):
        return hwmon_entry.devices and hwmon_entry.sensors and hwmon_entry.pwm_inputs


    def __list_hwmon(self):
        self.message('Listing hwmon:', styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        for entry in self.hwmon:
            self.message(self.SUBKEY_INDENT + entry.get_title(include_summary=True), styling=Logger.DEBUG)
        self.message()


    def __get_prompt_builder(self):
        builder = PromptBuilder(self.console, allowed_keystring=PromptBuilder.KEYSTRING_ALPHANUM)
        self.prompt_values = {}
        for entry in self.hwmon:
            key = builder.set_next(entry, highlight=entry.matches(self.fan_config.settings.dev_base), start_at=entry.suggest_key())
            self.prompt_values[key] = entry
        builder.add_back()
        return builder


    def __str__(self):
        return 'hwmon'