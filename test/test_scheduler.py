import unittest
from time import time
from lib.scheduler import MicroScheduler
from lib.exceptions import SchedulerLimitExceeded, NotScheduledException
from lib.logger import Logger, QueueLogger


class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.logger = QueueLogger(self.__class__.__name__, filter_level=Logger.DEBUG)
        self.step_delay = 20
        self.scheduler = MicroScheduler(self.logger, step_delay=self.step_delay)


    def test_limit(self, limit=5):
        self.scheduler.set_limit(limit)

        for i in range(limit):
            self.scheduler.set_next()

        self.assertRaises(SchedulerLimitExceeded, self.scheduler.set_next)

    
    def test_forgot_set_next(self):
        now = time()

        try:
            self.scheduler.was_passed(now)
            self.fail('exception not raised')
        except NotScheduledException:
            self.assertTrue(True)


    def test_was_passed(self):
        now = time()

        self.scheduler.set_next(now)
        now += self.step_delay + 1

        self.assertTrue(self.scheduler.was_passed(now))


    def test_was_passed_detect_past(self):
        now = time()

        self.scheduler.set_next(now)
        now -= 3600

        self.assertTrue(self.scheduler.was_passed(now))
        self.assertTrue(self.logger.includes_logged(None, Logger.WARNING))


    def test_was_passed_detect_future(self):
        now = time()

        self.scheduler.set_next(now)
        now += 3600

        self.assertTrue(self.scheduler.was_passed(now))
        self.assertTrue(self.logger.includes_logged(None, Logger.WARNING))


    def test_suggest_delay(self, num_steps=10):
        value = self.scheduler.suggest_step_delay(
            self.step_delay, 
            num_steps + 1
        )

        self.assertTrue(value <= (self.step_delay / num_steps))
        self.assertIsInstance(value, float)


    def test_suggest_delay_max(self, num_steps=10, max_length=0.5):
        value = self.scheduler.suggest_step_delay(
            self.step_delay, 
            num_steps + 1, 
            max_length
        )

        self.assertTrue(value <= (self.step_delay / num_steps))
        self.assertAlmostEqual(value, max_length)
        self.assertIsInstance(value, float)