import unittest
from lib.logger import Logger, QueueLogger, InteractiveLogger, PromptBuilder, ConfirmPromptBuilder
from lib import utils

class TestUtils(unittest.TestCase):

    def test_to_sentence(self):
        result = utils.to_sentence('Set', 'This', 'PWM')
        self.assertEqual(result, 'Set this PWM')