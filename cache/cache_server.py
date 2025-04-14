from flask import Flask, jsonify
from pymongo import MongoClient
from collections import OrderedDict
import threading

# Configuración
MONGO_URI = "mongodb://storage:27017"
CACHE_CAPACIDAD = 100
POLITICA = "LRU"  # Cambia a 'FIFO' si quieres probar otra política

app = Flask(__name__)

# Conexión a MongoDB
client = MongoClient(MONGO_URI)
db = client['waze_db']
coleccion = db['eventos']

# Cache en memoria
if POLITICA == "LRU":
    cache = OrderedDict()
else:
    cache = {}

# Lock para operaciones de escritura seguras
lock = threading.Lock()

# Contadores de métricas
cache_hits = 0
cache_misses = 0

def obtener_evento_por_id(evento_id):
    global cache_hits, cache_misses
    with lock:
        if evento_id in cache:
            cache_hits += 1
            print(f"✅ Cache HIT: {evento_id}")
            if POLITICA == "LRU":
                cache.move_to_end(evento_id)
            return cache[evento_id]
        else:
            cache_misses += 1
            print(f"❌ Cache MISS: {evento_id}")
            evento = coleccion.find_one({"id": evento_id})
            if evento:
                agregar_a_cache(evento_id, evento)
            return evento

def agregar_a_cache(evento_id, evento):
    if len(cache) >= CACHE_CAPACIDAD:
        if POLITICA == "LRU":
            removido = cache.popitem(last=False)
        elif POLITICA == "FIFO":
            clave_remover = next(iter(cache))
            removido = (clave_remover, cache.pop(clave_remover))
        print(f"🗑️ Removido del cache: {removido[0]}")
    cache[evento_id] = evento

@app.route('/evento/<string:evento_id>', methods=['GET'])
def obtener_evento(evento_id):
    evento = obtener_evento_por_id(evento_id)
    if evento:
        evento["_id"] = str(evento["_id"])
        return jsonify(evento)
    else:
        return jsonify({"error": "Evento no encontrado"}), 404

@app.route('/stats', methods=['GET'])
def obtener_estadisticas():
    with lock:
        return jsonify({
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "cache_tamaño": len(cache)
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
