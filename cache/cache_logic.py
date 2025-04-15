from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity=8):
        self.cache = OrderedDict()
        self.capacity = capacity
        self.hits = 0
        self.misses = 0

    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None

    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        elif len(self.cache) >= self.capacity:
            self.cache.popitem(last=False)
        self.cache[key] = value

    def __contains__(self, key):
        return key in self.cache

    def get_stats(self):
        return {
            "cache_hits": self.hits,
            "cache_misses": self.misses,
            "cache_tamano": len(self.cache)
        }
