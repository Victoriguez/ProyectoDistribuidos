import os
from flask import Flask, jsonify
from pymongo import MongoClient
from cache_logic import LRUCache
import logging

app = Flask(__name__)

# Leer variables de entorno
cache_size = int(os.getenv("CACHE_SIZE", 8))
policy = os.getenv("POLICY", "LRU")

# Selección de política (solo LRU implementado aquí)
if policy == "LRU":
    cache = LRUCache(cache_size)
else:
    raise ValueError(f"Política de cache no soportada: {policy}")

client = MongoClient("mongodb://mongo-storage:27017")
db = client["waze_db"]
collection = db["eventos"]

logging.basicConfig(level=logging.INFO, format="%(message)s")

@app.route('/evento/<string:event_id>', methods=['GET'])
def get_evento(event_id):
    logging.info(f"🔍 Consultando evento: {event_id}")
    if event_id in cache:
        logging.info(f"✅ HIT: {event_id}")
        return jsonify(cache.get(event_id))
    else:
        logging.warning(f"🆕 MISS: {event_id}")
        evento = collection.find_one({"id": event_id})
        if evento:
            logging.info(f"📥 Guardando en caché: {event_id}")
            cache.put(event_id, evento)
            return jsonify(evento)
        else:
            logging.error(f"❌ Evento no encontrado en la base de datos: {event_id}")
            return jsonify({"error": "Evento no encontrado"}), 404

@app.route('/metrics', methods=['GET'])
def metrics():
    stats = cache.get_stats()
    logging.info(f"📊 Métricas del caché: {stats}")
    return jsonify(stats)

if __name__ == '__main__':
    logging.info("🚀 Iniciando servidor de caché...")
    app.run(debug=True, host='0.0.0.0', port=5001)