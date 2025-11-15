import unittest
from lib.logger import Logger, QueueLogger, InteractiveLogger, PromptBuilder, ConfirmPromptBuilder


class TestInteractiveLogger(unittest.TestCase):
    def setUp(self):
        self.logger = QueueLogger(self.__class__.__name__, filter_level=Logger.ERROR)
        self.console = InteractiveLogger

    def test_prompt_highlight(self):
        builder = PromptBuilder(self.console)
        builder.set('a', 'option a', highlight=True)
        builder.set('b', 'option a', highlight=False)
        builder.set('x', 'option x', highlight=None)

        self.assertTrue(builder.should_highlight('x'))
        self.assertTrue(builder.should_highlight('a'))
        self.assertFalse(builder.should_highlight('b'))