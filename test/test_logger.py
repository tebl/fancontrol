import unittest
from lib.logger import Logger, QueueLogger


class TestLogger(unittest.TestCase):
    def setUp(self):
        self.logger = QueueLogger(self.__class__.__name__, filter_level=Logger.ERROR)


    def fill_log(self):
        for level in [Logger.ERROR, Logger.WARNING, Logger.INFO, Logger.DEBUG, Logger.VERBOSE]:
            self.logger.log(Logger.to_filter_level(level), level)


    def check_includes(self, log_level):
        return self.logger.includes_logged(Logger.to_filter_level(log_level), log_level)

    
    def test_error(self):
        self.logger.set_filter(Logger.ERROR)
        self.logger.clear()

        self.fill_log()

        self.assertTrue(self.check_includes(Logger.ERROR))
        self.assertEqual(len(self.logger.entries), 1)


    def test_warning(self):
        self.logger.set_filter(Logger.WARNING)
        self.logger.clear()

        self.fill_log()

        self.assertTrue(self.check_includes(Logger.ERROR))
        self.assertTrue(self.check_includes(Logger.WARNING))
        self.assertEqual(len(self.logger.entries), 2)


    def test_info(self):
        self.logger.set_filter(Logger.INFO)
        self.logger.clear()

        self.fill_log()

        self.assertTrue(self.check_includes(Logger.ERROR))
        self.assertTrue(self.check_includes(Logger.WARNING))
        self.assertTrue(self.check_includes(Logger.INFO))
        self.assertEqual(len(self.logger.entries), 3)


    def test_debug(self):
        self.logger.set_filter(Logger.DEBUG)
        self.logger.clear()

        self.fill_log()

        self.assertTrue(self.check_includes(Logger.ERROR))
        self.assertTrue(self.check_includes(Logger.WARNING))
        self.assertTrue(self.check_includes(Logger.INFO))
        self.assertTrue(self.check_includes(Logger.DEBUG))
        self.assertEqual(len(self.logger.entries), 4)


    def test_verbose(self):
        self.logger.set_filter(Logger.VERBOSE)
        self.logger.clear()

        self.fill_log()

        self.assertTrue(self.check_includes(Logger.ERROR))
        self.assertTrue(self.check_includes(Logger.WARNING))
        self.assertTrue(self.check_includes(Logger.INFO))
        self.assertTrue(self.check_includes(Logger.DEBUG))
        self.assertTrue(self.check_includes(Logger.VERBOSE))
        self.assertEqual(len(self.logger.entries), 5)


    def test_extra_verbose(self):
        level = Logger.VERBOSE+10
        self.logger.set_filter(level)
        self.logger.clear()

        self.fill_log()
        self.logger.log(Logger.to_filter_level(level), level)

        self.assertTrue(self.check_includes(Logger.ERROR))
        self.assertTrue(self.check_includes(Logger.WARNING))
        self.assertTrue(self.check_includes(Logger.INFO))
        self.assertTrue(self.check_includes(Logger.DEBUG))
        self.assertTrue(self.check_includes(Logger.VERBOSE))
        self.assertTrue(self.check_includes(level))
        self.assertEqual(len(self.logger.entries), 6)


    @staticmethod
    def to_filter_value(value):
        Logger.to_filter_value(value)


    def test_to_filter_value(self):
        self.assertEqual(Logger.to_filter_value('50'), Logger.INFO)
        self.assertEqual(Logger.to_filter_value('INFO'), Logger.INFO)
        self.assertRaises(ValueError, self.to_filter_value, 'xxx')
        self.assertRaises(ValueError, self.to_filter_value, '-1')