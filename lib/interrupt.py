import signal


class InterruptHandler(object):
    def __init__(self, signal_type=signal.SIGINT):
        self.signal_type = signal_type


    def __enter__(self):
        self.interrupted = False
        self.released = False
        self.original_handler = signal.getsignal(self.signal_type)

        def handler(signum, frame):
            self.release()
            self.interrupted = True
        
        signal.signal(self.signal_type, handler)
        return self


    def __exit__(self, exc_type, exc_value, traceback):
        self.release()


    def release(self):
        if self.released:
            return False
        
        signal.signal(self.signal_type, self.original_handler)
        self.released = True

        return True