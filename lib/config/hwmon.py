from ..exceptions import *
from ..logger import Logger, InteractiveLogger, PromptBuilder, ConfirmPromptBuilder
from ..hwmon import HwmonProvider
from .context import InteractiveContext


class HWMONContext(InteractiveContext):
    def __init__(self, *args):
        super().__init__(*args)
        self.hwmon_instances = []


    def interact(self, auto_select=None):
        self.summary()

        self.hwmon_instances = HwmonProvider.filter_instances(filter_func=self.__is_suitable)
        self.hwmon_list_providers(self.hwmon_instances, current_object=HwmonProvider.resolve_provider(self.fan_config.settings.dev_base))

        input = self.console.prompt_choices(self.__get_prompt_builder(), prompt=self, auto_select=auto_select)
        match input:
            case None | 'x':
                return self.parent
            case _:
                self.__change_hwmon(self.prompt_values[input])
                return self.parent
        return self


    def summary(self, items=None, sep=': ', prefix=InteractiveContext.SUBKEY_INDENT):
        # This is needed as changing items to a default value of [] would cause
        # it to be reused across all function calls. Apparently Python does that.
        if items is None:
            items = []

        self.parent.add_summary_logging(items)
        return super().summary(items, sep, prefix)


    def __is_suitable(self, hwmon_provider):
        return hwmon_provider.devices and hwmon_provider.sensors and hwmon_provider.pwm_inputs


    def __get_prompt_builder(self):
        builder = PromptBuilder(self.console, allowed_keystring=PromptBuilder.KEYSTRING_ALPHANUM)
        self.prompt_values = {}
        for entry in self.hwmon_instances:
            key = builder.set_next(entry, highlight=entry.matches(self.fan_config.settings.dev_base), start_at=entry.suggest_key())
            self.prompt_values[key] = entry
        builder.add_back()
        return builder


    def __change_hwmon(self, hwmon_provider):
        self.message()
        self.message('Changing to {}:'.format(str(hwmon_provider)), styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        self.message(self.SUBKEY_CHILD + 'Fan configurations will be disabled.', styling=Logger.DEBUG, end='\n\n')
        if self.console.prompt_choices(ConfirmPromptBuilder(self.console), prompt=self.CONFIRM_CHANGE) == 'y':
            self.fan_config.settings.set('Settings', 'dev_base', hwmon_provider.name)
            self.fan_config.settings.set('Settings', 'dev_name', hwmon_provider.get_driver_name())
            self.fan_config.settings.set('Settings', 'dev_path', hwmon_provider.get_driver_path())

            for section in self.fan_config.settings.sections():
                self.fan_config.settings.set_enabled(section, False)

            self.fan_config.settings.save()
            self.message(self.CONFIG_UPDATED, end='\n\n')


    def __str__(self):
        return 'hwmon'