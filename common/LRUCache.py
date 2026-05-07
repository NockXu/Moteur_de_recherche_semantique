from collections import OrderedDict

class LRUCache:
    def __init__(self, max_size: int = 256):
        self.cache = OrderedDict()
        self.max_size = max_size

    def get(self, key):
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def set(self, key, value):
        self.cache[key] = value
        self.cache.move_to_end(key)

        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)