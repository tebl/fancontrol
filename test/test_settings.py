import unittest, tempfile, os, string
from lib import Settings
from lib.logger import Logger, QueueLogger
from lib.exceptions import ControlRuntimeError
from pprint import pprint


class TestSettings(unittest.TestCase):
    DEFAULT_LEVEL = Logger.ERROR

    def setUp(self):
        self.logger = QueueLogger(self.__class__.__name__, filter_level=self.DEFAULT_LEVEL)
        self.temp_dir = tempfile.TemporaryDirectory(prefix='fancontrol-test-')
        self.base_path = self.temp_dir.name
        self.config_path = os.path.join(self.base_path, 'settings.ini')


    def dump_contents(self):
        with open(self.config_path, 'r') as file:
            print(file.read())


    def tearDown(self):
        self.temp_dir.cleanup()


    def test_create(self):
        s = Settings(self.config_path, self.logger, auto_create=False)
        self.assertFalse(os.path.isfile(self.config_path))

        s = Settings(self.config_path, self.logger)
        self.assertTrue(os.path.isfile(self.config_path))


    def test_invalid_characters(self):
        s = Settings(self.config_path, self.logger)
        with self.assertRaises(ControlRuntimeError):
            s.set(s.SETTINGS, 'ke@y', 'test')
        with self.assertRaises(ControlRuntimeError):
            s.set('secti@n', 'key', 'test')


    def test_strip_illegal(self):
        # Test stripping illegal characters. As we're using character lists to
        # test against, we sort the result to have something to match against
        v = 'amcxz'
        r = [c for c in v]
        r.sort()
        r = ''.join(r)

        s = Settings(self.config_path, self.logger, auto_create=False, allowed_chars=v)
        self.assertEqual(s.strip_illegal_chars(string.printable), r)


    def test_setter(self):
        s = Settings(self.config_path, self.logger, auto_create=False)
        v = 'test'
        s.set(s.SETTINGS, 'key', v)
        self.assertEqual(s.get(s.SETTINGS, 'key'), v)


    def test_sections(self):
        s = Settings(self.config_path, self.logger, auto_create=False)
        s.set('test_section', 'test', 'testvalue')
        
        # Check that this also created some default values
        self.assertTrue(s.get('test_section', 'enabled'))

        # Examine main settings
        self.assertTrue(s.have_section(s.SETTINGS))
        self.assertTrue(s.have_key(s.SETTINGS, 'log_level'))

        # Test that we only return enabled sections
        s.set('test_section', 'enabled', 'yes')
        self.assertEqual(s.sections(only_enabled=True), ['test_section'])

        # Test that it then disappears
        s.set('test_section', 'enabled', 'no')
        self.assertEqual(s.sections(only_enabled=True), [])

        # Test filtering out sections based on only_enabled, note that
        # this also eliminates the Settings-entry itself.
        self.assertEqual(s.sections(filter_special=False, only_enabled=False), [s.SETTINGS, 'test_section'])
        self.assertEqual(s.sections(filter_special=False, only_enabled=True), [])

        # Finally, delete the remaining section
        s.remove_section('test_section')
        self.assertEqual(s.sections(filter_special=True, only_enabled=False), [])


    def test_rename_section(self, section='test_section', section_new='test_second', section_existing='test_existing', test_key='test', test_value='test value'):
        s = Settings(self.config_path, self.logger, auto_create=False)
        s.set(s.SETTINGS, test_key, test_value)
        s.set(section, test_key, test_value)
        self.assertEqual(s.get('test_section', test_key), test_value)

        # New name empty
        with self.assertRaises(ControlRuntimeError):
            s.rename_section(section, '')

        # Try to overwrite special
        with self.assertRaises(ControlRuntimeError):
            s.rename_section(section, s.SETTINGS)

        # Try to overwrite existing
        s.set(section_existing, test_key, test_value)
        with self.assertRaises(ControlRuntimeError):
            s.rename_section(section, section_existing)

        # Actually do it
        s.rename_section(section, section_new)

        # Verify that entries moved
        self.assertFalse(s.have_section(section))
        self.assertTrue(s.have_section(section_new))
        self.assertEqual(s.get(section_new, test_key), test_value)

        # Check that we didn't destroy anything vital
        self.assertEqual(s.get(s.SETTINGS, test_key), test_value)
        for key in [ 'log_level', 'log_using', 'log_formatter', 'delay' ]:
            self.assertTrue(s.have_key(s.SETTINGS, key))


    @unittest.skip('Does not work')
    def test_settings_reconfigure(self):
        self.logger.set_filter(Logger.STR_ERROR)
        self.assertEqual(self.logger.filter_level, Logger.ERROR)

        s = Settings(self.config_path, self.logger, auto_write=False)
        s.set(s.SETTINGS, 'log_level', Logger.STR_VERBOSE)
        s.save

        s = Settings(self.config_path, self.logger, auto_write=False, reconfigure_logger=True)
        s.set(s.SETTINGS, 'log_level', Logger.STR_VERBOSE)
        self.assertEqual(self.logger.filter_level, Logger.VERBOSE)
