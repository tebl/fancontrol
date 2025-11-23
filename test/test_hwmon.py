import unittest
from lib.logger import Logger, QueueLogger, InteractiveLogger, PromptBuilder, ConfirmPromptBuilder
from lib.hwmon_info import HwmonProvider, HwmonInfo


class TestHwmon(unittest.TestCase):
    def test_hwmon(self):
        results = HwmonProvider.load_instances()
        self.assertIsInstance(results, list)