import contextlib
import signal


@contextlib.contextmanager
def uninterruptible():
    s = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, s)
