import unittest
from lib.logger import Logger, QueueLogger, InteractiveLogger, PromptBuilder, ConfirmPromptBuilder
from lib import utils, PWMIterator


class TestPWMIterator(unittest.TestCase):
    def test_iterator_length(self):
        # Check that we have all values
        iterator = PWMIterator(PWMIterator.PWM_MIN, PWMIterator.PWM_MAX, 1)
        values = [v for v in iter(iterator)]
        self.assertTrue(len(values) == 256)


    def test_iterator_forward(self):
        # Forward iteration
        iterator = PWMIterator(PWMIterator.PWM_MIN, PWMIterator.PWM_MAX, 20)
        values = [v for v in iter(iterator)]
        self.assertTrue(values[0] == PWMIterator.PWM_MIN)
        self.assertTrue(values[-1] == PWMIterator.PWM_MAX)


    def test_iterator_reverse(self):
        # Reverse iteration
        iterator = PWMIterator(PWMIterator.PWM_MIN, PWMIterator.PWM_MAX, -20)
        values = [v for v in iter(iterator)]
        self.assertTrue(values[-1] == PWMIterator.PWM_MIN)
        self.assertTrue(values[0] == PWMIterator.PWM_MAX)
