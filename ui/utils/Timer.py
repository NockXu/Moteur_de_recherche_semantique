import time

class Timer:
    """A lightweight execution profiling utility for measuring code execution loops.

    Maintains high-precision monotonic timeline marks to calculate intermediate intervals
    between sequential milestones.
    """
    
    def __init__(self):
        """Initialize the execution timer and record the baseline timestamp."""
        self.last = time.perf_counter()

    def checkpoint(self, name):
        """Measure, log, and update the time delta since the preceding checkpoint reference point.

        Args:
            name (str): The descriptive label or milestone identifier for the tracking segment.
        """
        now = time.perf_counter()
        print(f"[TIME] {name} → {(now - self.last)*1000:.2f} ms")
        self.last = now