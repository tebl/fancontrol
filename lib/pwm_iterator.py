class PWMIterator:
    '''
    Standard range functions in Python _really_ does not want to deal with
    ranges that should include start and stop - so that's what this is. Step
    is used to set incremented amount, but the outer bounds are limited to
    start and end so we may end up with a partial last step for values that
    aren't directly divisible. Use of a negative step also reverses start and
    end so that we count down instead.
    '''
    PWM_MIN = 0
    PWM_MAX = 255


    def __init__(self, start, end, step):
        self.start = start
        self.end = end
        self.step = step
        self.started = False


    def __iter__(self):
        self.value = self.start if self.step > 0 else self.end
        return self


    def __next__(self):
        if not self.started:
            self.started = True
            return self.value

        if self.step > 0:
            # Positive iterator
            if self.value == self.end:
                raise StopIteration
            self.value += self.step
            if self.value > self.end:
                self.value = self.end
            return self.value

        # Negative iterator
        if self.value == self.start:
            raise StopIteration
        self.value += self.step
        if self.value < self.start:
            self.value = self.start
        return self.value
