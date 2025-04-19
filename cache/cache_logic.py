from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity=8):
        self.cache = OrderedDict()
        self.capacity = capacity
        self.hits = 0
        self.misses = 0

    def get(self, key):
        print(f"Consultando clave: {key}")
        if key in self.cache:
            self.cache.move_to_end(key)
            self.hits += 1
            print(f"HIT: {key}")
            return self.cache[key]
        else:
            self.misses += 1
            print(f"MISS: {key}")
            return None

    def put(self, key, value):
        print(f"Guardando clave en caché: {key}")
        if key in self.cache:
            self.cache.move_to_end(key)
        elif len(self.cache) >= self.capacity:
            eliminado = self.cache.popitem(last=False)
            print(f"Eliminado del caché: {eliminado[0]}")
        self.cache[key] = value

    def __contains__(self, key):
        return key in self.cache

    def get_stats(self):
        print(f"Cache stats - Hits: {self.hits}, Misses: {self.misses}, Tamaño: {len(self.cache)}")
        return {
            "cache_hits": self.hits,
            "cache_misses": self.misses,
            "cache_tamano": len(self.cache)
        }

class FIFOCache:
    def __init__(self, capacity=8):
        self.cache = OrderedDict()
        self.capacity = capacity
        self.hits = 0
        self.misses = 0

    def get(self, key):
        print(f"Consultando clave: {key}")
        if key in self.cache:
            self.hits += 1
            print(f"HIT: {key}")
            return self.cache[key]
        else:
            self.misses += 1
            print(f"MISS: {key}")
            return None

    def put(self, key, value):
        print(f"Guardando clave en caché: {key}")
        if key not in self.cache and len(self.cache) >= self.capacity:
            eliminado = self.cache.popitem(last=False)
            print(f"Eliminado del caché: {eliminado[0]}")
        self.cache[key] = value

    def __contains__(self, key):
        return key in self.cache

    def get_stats(self):
        print(f"Cache stats - Hits: {self.hits}, Misses: {self.misses}, Tamaño: {len(self.cache)}")
        return {
            "cache_hits": self.hits,
            "cache_misses": self.misses,
            "cache_tamano": len(self.cache)
        }