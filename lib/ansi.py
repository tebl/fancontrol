class ANSIFormatter:
    MONOCHROME = "MONO"
    BASIC = "BASIC"
    EXPANDED = "EXPANDED"
    ALLOWED = [ MONOCHROME, BASIC, EXPANDED ]

    FG_BASE = 30
    FG_BRIGHT = 90

    BG_BASE = 40
    BG_BRIGHT = 100

    COLOUR_BLACK = 0
    COLOUR_RED = 1
    COLOUR_GREEN = 2
    COLOUR_YELLOW = 3
    COLOUR_BLUE = 4
    COLOUR_MAGENTA = 5
    COLOUR_CYAN = 6
    COLOUR_WHITE = 7


    def __init__(self, features=BASIC):
        self.set_features(features)
            
    
    def set_features(self, features):
        self.is_monochrome = (features == self.MONOCHROME)
        self.use_16 = (features == self.BASIC) and not self.is_monochrome
        self.use_256 = (features == self.EXPANDED) and not self.is_monochrome


    def ansi_code(self, code):
        if type(code) is list:
            code = ';'.join([str(v) for v in code])
        return '\x1b[' + str(code) +'m'


    def ansi_wrap(self, codes, text):
        return self.ansi_code(codes) + text + self.ansi_code(0)


    def ansi_start(self, codes, text):
        return self.ansi_code(codes)


    def ansi_end(self):
        return self.ansi_code(0)


    def colour(self, base, offset):
        return base + offset
    

    def fg_colour(self, offset, bright=False):
        if bright:
            return self.colour(self.FG_BASE, offset)
        return self.colour(self.FG_BRIGHT, offset)


    def bg_colour(self, offset, bright=False):
        if bright:
            return self.colour(self.BG_BASE, offset)
        return self.colour(self.BG_BRIGHT, offset)


    def fg_colour_256(self, colour_number):
        return [38, 5, colour_number]


    def bg_colour_256(self, colour_number):
        return [48, 5, colour_number]



    def in_regular(self, str):
        return str


    def get_wrap_func(self, wrap_func):
        if wrap_func is None:
            return self.ansi_wrap
        return wrap_func

    def in_verbose(self, str, wrap_func=None):
        wrap_func = self.get_wrap_func(wrap_func)
        if self.use_256:
            return wrap_func(self.fg_colour_256(242), str)
        return wrap_func([2, self.fg_colour(self.COLOUR_BLACK)], str)


    def in_debug(self, str, wrap_func=None):
        wrap_func = self.get_wrap_func(wrap_func)
        if self.use_256:
            return wrap_func(self.fg_colour_256(248), str)
        return wrap_func([2, self.fg_colour(self.COLOUR_BLACK)], str)


    def in_info(self, str, wrap_func=None):
        wrap_func = self.get_wrap_func(wrap_func)
        if self.use_256:
            return wrap_func(self.fg_colour_256(255), str)
        return wrap_func(self.fg_colour(self.COLOUR_WHITE), str)


    def in_warning(self, str, wrap_func=None):
        wrap_func = self.get_wrap_func(wrap_func)
        if self.use_256:
            return wrap_func(self.fg_colour_256(220), str)
        return wrap_func(self.fg_colour(self.COLOUR_YELLOW), str)


    def in_error(self, str, wrap_func=None):
        wrap_func = self.get_wrap_func(wrap_func)
        if self.use_256:
            return wrap_func(self.fg_colour_256(160), str)
        return wrap_func(self.fg_colour(self.COLOUR_RED), str)
    

    def in_prompt(self, str, wrap_func=None):
        return self.in_info(str, wrap_func=wrap_func)


    def in_highlight(self, str, wrap_func=None):
        return self.in_debug(str, wrap_func=wrap_func)
    

    def in_value(self, str, wrap_func=None):
        return self.in_warning(str, wrap_func=wrap_func)