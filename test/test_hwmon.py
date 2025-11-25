import os, unittest
from pprint import pprint
from lib.logger import Logger, QueueLogger, InteractiveLogger, PromptBuilder, ConfirmPromptBuilder
from lib.hwmon import HwmonProvider, HwmonInfo, HwmonNvidia


class TestHwmon(unittest.TestCase):
    def setUp(self):
        if not self.have_hwmon():
            self.skipTest('system does not have hwmon entries')


    def have_hwmon(self):
        if os.path.isdir(HwmonInfo.BASE_PATH):
            for dirpath, dirnames, filenames in os.walk(HwmonInfo.BASE_PATH):
                for entry in dirnames:
                    return True
        return False


    def test_hwmon(self):
        providers = HwmonProvider.load_instances()
        self.assertIsInstance(providers, list)
        for provider in providers:
            self.assertIsInstance(provider.get_title(include_summary=True), str)


    def test_wrong_parser(self):
        result = HwmonInfo.try_parsing_value('/virtual/nvidia/nvidia0/temp0', '/sys/class/hwmon/hwmon4')
        self.assertIsNone(result)

        result = HwmonNvidia.try_parsing_value('pwm4', '/sys/class/hwmon/hwmon4')
        self.assertIsNone(result)



    def test_hwmon_info_parse_value(self):
        def test_hwmon(value, dev_base):
            result1 = HwmonProvider.parse_value(value, dev_base)
            self.assertIsNotNone(result1)
            result2 = HwmonInfo.try_parsing_value(value, dev_base)
            self.assertIsNotNone(result2)
            self.assertEqual(result1, result2)
            return result2

        hwmon, entry = test_hwmon('fan3_input', '/sys/class/hwmon/hwmon4')
        self.assertEqual(hwmon, 'hwmon4')
        self.assertEqual(entry, 'fan3_input')

        hwmon, entry = test_hwmon('/sys/class/hwmon/hwmon0/pwm3', '/sys/class/hwmon/hwmon4')
        self.assertEqual(hwmon, 'hwmon0')
        self.assertEqual(entry, 'pwm3')

        hwmon, entry = test_hwmon('pwm3', '/sys/class/hwmon/hwmon6')
        self.assertEqual(hwmon, 'hwmon6')
        self.assertEqual(entry, 'pwm3')


    def test_hwmon_nvidia_parse_value(self):
        def test_hwmon(value, dev_base):
            result1 = HwmonProvider.parse_value(value, dev_base)
            self.assertIsNotNone(result1)
            result2 = HwmonNvidia.try_parsing_value(value, dev_base)
            self.assertIsNotNone(result2)
            self.assertEqual(result1, result2)
            return result2

        hwmon, entry = test_hwmon('/virtual/nvidia0/temp0', '/sys/class/hwmon/hwmon4')
        self.assertEqual(hwmon, 'nvidia0')
        self.assertEqual(entry, 'temp0')

        hwmon, entry = test_hwmon('temp0', '/virtual/nvidia0')
        self.assertEqual(hwmon, 'nvidia0')
        self.assertEqual(entry, 'temp0')


    def test_hwmon_validation(self):
        # Get all of them. Note that the entire set of tests will be disabled
        # we don't have any hwmon-entries, so we should have at least one.
        providers = HwmonInfo.load_instances()
        validation_hwmon_name = providers[0].name

        def validation_func(entry):
            return entry.matches(validation_hwmon_name)

        filtered = HwmonInfo.load_instances(validation_func=validation_func)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].name, validation_hwmon_name)
    

    def test_hwmon_nvidia(self):
        providers = HwmonNvidia.load_instances()
        self.assertIsInstance(providers, list)
        for provider in providers:
            self.assertIsInstance(provider.get_title(include_summary=True), str)

            for sensor in provider.sensors:
                print(sensor.get_title(include_summary=True, include_value=True))
                self.assertIsInstance(sensor.get_title(include_summary=True, include_value=True), str)
