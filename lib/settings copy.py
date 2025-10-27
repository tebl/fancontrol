import os
import yaml
from .logger import Logger, LoggerMixin

class Settings(LoggerMixin):
    def __init__(self, config_path, logger):
        self.set_logger(logger)
        self.config_path = config_path
        self.dirty = False
        self.values = {
            'log_level': Logger.INFO,
            'fans': {
                'System Fan #1'
            }
        }
        self.read_settings()

    # def __getattr__(self, attr):
    #     pass

    def __setattr__(self, name, value):
        if name == 'log_level':
            self.configure_log_level(value)
        return super().__setattr__(name, value)

    def read_settings(self):
        if not os.path.isfile(self.config_path):
            return
        
        with open(self.config_path) as file:
            data = yaml.safe_load(file)
            self.values.update(data)
        # self.config.read(self.config_path)

    def save(self):
        with open(self.config_path, 'w') as file:
            yaml.dump(self.values, file, default_flow_style=False)
        self.dirty = False

    def import_configuration(self, input_path):
        self.log_info("Importing from", input_path)
        self.save()