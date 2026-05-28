from queue import Queue


class EventQueue:
    """
    Thread-safe bridge between the audio callback thread
    and the main thread.

    The audio thread pushes events in.
    The main thread pops events out.
    The Queue handles all thread coordination internally.
    """

    def __init__(self):
        self._queue = Queue()

    def push(self, event):
        """Called from the audio thread."""
        self._queue.put(event)

    def pop(self):
        """
        Called from the main thread.
        Returns the next event, or None if the queue is empty.
        Non-blocking — never waits.
        """
        if not self._queue.empty():
            return self._queue.get()
        return None