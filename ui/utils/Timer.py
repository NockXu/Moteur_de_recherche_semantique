import time

class Timer:
    def __init__(self):
        self.last = time.perf_counter()

    def checkpoint(self, name):
        now = time.perf_counter()
        print(f"[TIME] {name} → {(now - self.last)*1000:.2f} ms")
        self.last = now