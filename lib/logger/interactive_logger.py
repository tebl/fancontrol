import sys, tty, termios, fcntl, struct, string, math
from . import Logger, ConsoleLogger
from .. import utils


class PromptBuilder:
    '''
    Helper class used with InteractiveLogger.prompt_choices to present the user
    with a defined set of options, then repeat the question until they select a
    valid one. Also takes care of printing option legend.

    builder = PromptBuilder(interactive_logger)
    builder.set_next('option 1')
    builder.set_next('option 2')
    builder.set('x', 'Return')

    input = self.logger.prompt_choices(builder)
    if input == 'x':
        return
    else:
        print('You entered ' + input)    
    '''
    KEYSTRING_ALPHANUM = string.digits + string.ascii_lowercase
    KEYSTRING_NATURAL = string.digits[1:] + '0' + string.ascii_lowercase
    DEFAULT_KEYSTRING = KEYSTRING_NATURAL


    def __init__(self, interactive_logger, init_with=[], allowed_keystring=None):
        self.data = {}
        self.data_highlight = {}
        self.logger = interactive_logger
        self.default_key = None

        # Setting up valid option keys, then use that to build list of 
        # available keys.
        self.allowed_keystring = self.DEFAULT_KEYSTRING
        if allowed_keystring is not None:
            self.allowed_keystring = allowed_keystring
        self.available_keys = [c for c in self.allowed_keystring]

        # Initialize options specified directly
        for key, value in init_with:
            self.set(key, value)


    def get(self, key, default_on_missing=None):
        '''
        Get specified prompt if it exists. A default value can be specified in
        case it doesn't, but note that keys will also remove any None-values.
        '''
        if key in self.data:
            return self.data[key]
        return default_on_missing


    def set(self, key, value=None, highlight=None, add_missing_key=False, reorder=False):
        '''
        Set prompt key to a value. Note that while a value of None will cause
        the key to be left out when explocitly listing the keys, it will also
        remove it from the list of available keys - this is to allow the removal
        of certain keys.
        '''
        # Handle missing keys
        if key not in self.allowed_keystring:
            if not add_missing_key:
                raise ValueError(utils.to_keypair_str('invalid key specified', key))
            self.allowed_keystring += key
        
        # Reorder as last key, keeps system functions from drowning in a list
        if reorder:
            index = self.allowed_keystring.index(key)
            self.allowed_keystring = self.allowed_keystring[:index] + self.allowed_keystring[index+1:] + key

        # Remove key from automatic assignment
        if key in self.available_keys:
            self.available_keys.remove(key)
        
        # Set new highlight, but don't overwrite without a value
        if highlight is not None:
            self.set_highlight(key, highlight)

        # Set the actual value
        self.data[key] = value
        return self
    

    def set_default(self, key):
        '''
        Prompt builder can be used to suggest a default key option, this is
        handy when we either only have a single option available - or - we
        want to default to the currently set value.
        '''
        if key not in self.data:
            raise ValueError('key {} is not set'.format(key))
        self.default_key = key


    def get_default(self):
        '''
        '''
        return self.default_key


    def add_exit(self, value='Exit', highlight=True, reorder=False):
        return self.set('x', value=value, highlight=highlight, reorder=reorder)


    def add_cancel(self, highlight=True, reorder=False):
        return self.add_exit(value='Cancel', highlight=highlight, reorder=reorder)


    def add_back(self, highlight=True, reorder=False):
        return self.add_exit(value='Back', highlight=highlight, reorder=reorder)


    def set_next(self, value, start_at=None, highlight=None):
        '''
        Get next available option key, then set the specified value using it.
        '''
        key = self.next_key(start_at=start_at)
        self.set(key, value, highlight=highlight)
        return key


    def next_key(self, start_at=None):
        '''
        Get a unique key for use, also removes it as a candidate for set_next.
        '''
        if start_at and start_at in self.allowed_keystring:
            index = self.allowed_keystring.find(start_at)
            for char in self.allowed_keystring[index:]:
                if char in self.available_keys:
                    self.available_keys.remove(char)
                    return char

        return self.available_keys.pop(0)


    def keys(self):
        '''
        Retrieves a list of prompt options that exists. Note that we can
        reserve a key using None as the value to keep it from being used,
        that's why we're filtering them out here.
        '''
        return [char for char in self.allowed_keystring if self.get(char) is not None]
    

    def should_highlight(self, key, default=False, default_for_x=True):
        '''
        Implements a method of determining which options should be highlighted
        instead of serving as regular values, these are normally special values
        and not actual values. Data takes precedence over default values
        specified.
        '''
        if key in self.data_highlight:
            return self.data_highlight[key]
        elif key == 'x':
            return default_for_x
        return default


    def set_highlight(self, key, value):
        self.data_highlight[key] = value


    def print_legend(self, column_spacing=2):
        '''
        Print prompt legend. Attempts to put as much on a single-line as
        possible with some space to spare, but will adapt to the length
        of values supplied to it.
        '''
        options = []
        highlight = []
        for key in self.keys():
            options.append('{}) {}'.format(key, str(self.get(key))))
            highlight.append(self.should_highlight(key))

        # Get the longest prompt entry, round up to 10 spaces
        max_length = len(max(options, key=len))
        max_length = 10 * math.ceil(max_length / 10)

        term_width, term_height = self.logger.get_terminal_size()
        term_columns = 2
        while True:
            # Combined size of content, then add column spacing
            combined = term_columns * max_length
            combined += (term_columns - 1) * column_spacing

            if (combined > term_width):
                term_columns -= 1
                break
            term_columns += 1


        while options:
            for column in range(term_columns):
                if options:
                    entry = options.pop(0)
                    entry = entry.ljust(max_length)

                    # Highlight some entries as specified
                    if highlight.pop(0):
                        self.logger.log_direct(entry, InteractiveLogger.DIRECT_OPTION_HIGHLIGHT, end='')
                    else:
                        self.logger.log_direct(entry, InteractiveLogger.DIRECT_OPTION, end='')

                    if column < (term_columns - 1):
                        self.logger.log_direct(' ' * column_spacing, end='')
            self.logger.log_direct('')


    @staticmethod
    def ensure_keystring(required_keystring, specified_keystring):
        '''
        Mainly used in order to validate allowed_keystring values when supplied
        via inheriting classes.
        '''
        missing = [char for char in required_keystring if not char in specified_keystring]
        if missing:
            raise ValueError(utils.to_keypair_str('allowed_keystring missing required values', ', '.join(missing)))


    def __contains__(self, key):
        '''
        Allows us to easily check if we have this option set by doing:
            if key in instance:
                ...
        '''
        return key in self.data


class ConfirmPromptBuilder(PromptBuilder):
    def __init__(self, interactive_logger, init_with=[], allowed_keystring=None, include_cancel=True):
        required_keystring = 'ynx' if include_cancel else 'yn'
        if allowed_keystring is None:
            allowed_keystring = required_keystring
        self.ensure_keystring(required_keystring, allowed_keystring)

        super().__init__(interactive_logger, init_with, allowed_keystring)
        self.set('y', 'Yes')
        self.set('n', 'No')
        if include_cancel:
            self.set('x', 'Cancel', highlight=True)


class PromptValidationException(Exception):
    '''
    Used when calls to from InteractiveLogger prompts fail validation, ie. the
    user input some value that doesn't appear to have the correct format.
    '''
    def __init__(self, message):
        super().__init__(message)
        self.message = message

    
    def __str__(self):
        return self.message


class InteractiveLogger(ConsoleLogger):
    '''
    Similar to ConsoleLogger except we're only relying on colorized output to
    tell entries apart.
    '''
    LF = "\x0a"
    CR = "\x0d"
    SPACE = "\x20"
    ESC = "\x1b"
    TAB = "\x09"
    CTRL_C = "\x03"
    BACKSPACE = "\x7f"

    DIRECT_REGULAR = 1000
    DIRECT_HIGHLIGHT = 1001
    DIRECT_OPTION = 1010
    DIRECT_OPTION_HIGHLIGHT = 1011
    DIRECT_VALUE = 1020
    DIRECT_PROMPT = 1030


    def __init__(self, log_name, filter_level=Logger.INFO, auto_flush=False, formatter=None):
        super().__init__(log_name, filter_level, auto_flush, formatter)


    def log_direct(self, message, styling=DIRECT_REGULAR, end='\n'):
        if self.formatter and not self.formatter.is_monochrome:
            message = self.format_ansi(message, styling)
        print(message, flush=self.auto_flush, end=end)


    def log_error(self, message, end='\n'):
        self.log_direct(message, styling=Logger.ERROR, end=end)


    def get_format_func(self, entry_type):
        if entry_type >= self.DIRECT_REGULAR:
            match entry_type:
                case self.DIRECT_REGULAR:
                    return self.formatter.in_regular
                case self.DIRECT_HIGHLIGHT:
                    return self.formatter.in_highlight
                case self.DIRECT_VALUE:
                    return self.formatter.in_value
                case self.DIRECT_OPTION:
                    return self.formatter.in_option
                case self.DIRECT_OPTION_HIGHLIGHT:
                    return self.formatter.in_option_highlight
                case self.DIRECT_PROMPT:
                    return self.formatter.in_prompt
        return super().get_format_func(entry_type)


    def format_logline(self, message, log_level):
        '''
        Ensures that we can tell things apart before logging them, if we're not
        sure we use ConsoleLogger function to ensure that we're adding tags
        instead.
        '''
        if self.formatter and not self.formatter.is_monochrome:
            return self.format_ansi(message, log_level)
        return super().format_logline(message, log_level)


    def prompt_choices(self, prompt_builder, prompt='Select option'):
        prompt_builder.print_legend()
        self.log_prompt(prompt)
        while True:
            result = self.get_character()
            if result == self.BACKSPACE:
                result = 'x'

            default = prompt_builder.get_default()
            if result == self.LF and default is not None:
                result = default
                
            if result in prompt_builder:
                self.log_direct(result, styling=self.DIRECT_VALUE)
                return result


    def prompt_character(self, prompt):
        self.log_prompt(prompt)
        result = self.get_character()
        self.log_direct(result, styling=self.DIRECT_VALUE)
        return result


    def prompt_input(self, prompt, allow_blank=True, validation_func=None):
        '''
        Prompt the user for input, if provided a custom validation function can
        be provided. Validation-function will be considered succesful if it
        completes without raising a PromptValidationException.
        '''
        last_error = None
        while True:
            self.log_prompt(prompt, last_error)
            try:
                self.formatted_start('in_value')
                result = input()
            finally:
                self.formatted_end()

            if allow_blank and result == '':
                return None
            if validation_func is not None:
                valid = False
                try:
                    validation_func(result)
                    valid = True
                except PromptValidationException as ve:
                    last_error = str(ve)

                if valid:
                    return result
                else:
                    self.clear_previous_line()
                    continue

            return result


    def log_prompt(self, prompt, last_error=None):
        if last_error is None:
            self.log_direct('{}: '.format(prompt), styling=self.DIRECT_PROMPT, end='')
            return
        self.log_direct(prompt + ' (', styling=self.DIRECT_PROMPT, end='')
        self.log_direct(last_error, styling=Logger.ERROR, end='')
        self.log_direct('): ', styling=self.DIRECT_PROMPT, end='')


    def get_character(self):
        '''
        Reconfigure terminal for raw control, read a single character then
        restore previous terminal settings. The character read is returned
        from the function.

        Based on the following blog post:
        https://love-python.blogspot.com/2010/03/getch-in-python-get-single-character.html
        '''
        fd = sys.stdin.fileno()

        oldterm = termios.tcgetattr(fd)
        newattr = termios.tcgetattr(fd)
        newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, newattr)

        oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)

        try:
            return sys.stdin.read(1)
        except IOError:
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
            fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)


    def get_terminal_size(self):
        '''
        Extract terminal dimensions from the system.
        '''
        th, tw, hp, wp = struct.unpack('HHHH', fcntl.ioctl(0, termios.TIOCGWINSZ, struct.pack('HHHH', 0, 0, 0, 0)))
        return tw, th


    def formatted_start(self, format_func_string):
        '''
        Set terminal style using formatter function with the name as specified
        using format_func_string. Yes, I know it's weird - it was simply the
        easiest way of specifying it without needing more code setting it up
        than what we'd be replacing.

        The function specified should have a set method structure, and was
        designed with ANSIFormatter().in_<style>(self, str, wrap_func=None) in
        mind.
        '''
        if self.formatter is None:
            return
        format_func = getattr(self.formatter, format_func_string)
        if callable(format_func):
            self.log_direct(format_func('', wrap_func=self.formatter.ansi_start), end='')


    def formatted_end(self):
        '''
        Resets _all_ terminal style, not just whatever was specified using
        formatted_start. This is an important distinction.
        '''
        if self.formatter is None:
            return
        self.log_direct(self.formatter.ansi_end(), end='')

    
    def clear_previous_line(self):
         # Move cursor up 
        sys.stdout.write("\033[F")
         # Clear line
        sys.stdout.write("\033[K")