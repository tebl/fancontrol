import os
from ..logger import Logger, InteractiveLogger, PromptBuilder, ConfirmPromptBuilder
from ..exceptions import ControlRuntimeError
from ..control import BaseControl
from ..hwmon_info import HwmonInfo
from .context import InteractiveContext


class SectionPWMInputContext(InteractiveContext):
    def __init__(self, *args, section):
        super().__init__(*args)
        self.section = section


    def interact(self):
        self.__summarise(self.fan_config.settings)

        input = self.console.prompt_choices(self.__get_prompt_builder(), prompt=self.section)
        match input:
            case None | 'x':
                return self.parent
            case 's':
                return self.__set_pwm_input()
        return self


    def __summarise(self, config):
        self.summarise([
            ['Name', self.section],
            ["PWM Input", config.get(self.section, 'pwm_input'), InteractiveLogger.DIRECT_HIGHLIGHT]
        ])


    def __get_prompt_builder(self):
        builder = PromptBuilder(self.console)
        builder.add_back()
        builder.set('s', 'Set PWM Input')
        return builder


    def __set_pwm_input(self):
        self.message()
        self.message('Select hwmon entry:', styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        hwmon_info = self.__select_hwmon(self.fan_config.settings.dev_base)
        if not hwmon_info:
            return self
        is_current_hwmon = hwmon_info.matches(self.fan_config.settings.dev_base)
        current_pwm_input=self.fan_config.settings.get(self.section, 'pwm_input')

        self.message()
        self.message('Select new PWM Input:', styling=InteractiveLogger.DIRECT_HIGHLIGHT)
        pwm_input = self.__select_pwm_input(
            hwmon_info, 
            is_current_hwmon=is_current_hwmon, 
            current_pwm_input=current_pwm_input
        )

        if not pwm_input:
            return self

        self.fan_config.settings.set(self.section, 'pwm_input', pwm_input.input)
        self.fan_config.settings.save()
        self.message('Configuration updated.', end='\n\n')

        return self
    

    def __select_hwmon(self, current):
        hwmon_list = []
        for dirpath, dirnames, filenames in os.walk(BaseControl.BASE_PATH):
            dirnames.sort()
            for dir in dirnames:
                hwmon_entry = HwmonInfo(dir, os.path.join(BaseControl.BASE_PATH, dir))
                if self.__is_hwmon_suitable(hwmon_entry):
                    hwmon_list.append(hwmon_entry)
            break

        builder = PromptBuilder(self.console)
        builder.add_back()
        choices = {}
        for hwmon_entry in hwmon_list:
            highlight = hwmon_entry.matches(current)
            key = builder.set_next(hwmon_entry.get_title(), start_at=hwmon_entry.suggest_key(), highlight=highlight)
            choices[key] = hwmon_entry
        
        selected = self.console.prompt_choices(builder, prompt='Select hwmon')
        match selected:
            case None | 'x':
                return None
            case _:
                return choices[selected]
        return None


    def __is_hwmon_suitable(self, hwmon_entry):
        return hwmon_entry.pwm_inputs


    def __select_pwm_input(self, hwmon_info, is_current_hwmon, current_pwm_input):
        builder = PromptBuilder(self.console)
        builder.add_back()
        choices = {}
        for entry in hwmon_info.pwm_inputs:
            highlight = True if is_current_hwmon and entry.matches(current_pwm_input) else False
            key = builder.set_next(str(entry), highlight=highlight)
            choices[key] = entry

        selected = self.console.prompt_choices(builder, prompt='Select PWM Input')
        match selected:
            case None | 'x':
                return None
            case _:
                return choices[selected]
        return None
