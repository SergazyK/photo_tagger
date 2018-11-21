import threading

class SingleExec(contextlib.ContextDecorator):
    def __init__(self, lock=None):
        if lock:
            self.lock = lock
        else:
            self.lock = threading.Lock()

    def __enter__(self):
        self.lock.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()
