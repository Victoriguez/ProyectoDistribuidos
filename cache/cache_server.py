import os
from flask import Flask, jsonify
from pymongo import MongoClient
from bson import ObjectId
from cache_logic import LRUCache, FIFOCache
import logging

app = Flask(__name__)

# Leer variables de entorno
cache_size = int(os.getenv("CACHE_SIZE", 8))
policy = os.getenv("POLICY", "LRU")

# Selección de política
if policy == "LRU":
    cache = LRUCache(cache_size)
elif policy == "FIFO":
    cache = FIFOCache(cache_size)
else:
    raise ValueError(f"Política de cache no soportada: {policy}")

# Conexión a MongoDB
try:
    client = MongoClient("mongodb://mongo-storage:27017")
    db = client["waze_db"]
    collection = db["eventos"]
    logging.info("✅ Conexión a MongoDB establecida.")
except Exception as e:
    logging.error(f"❌ Error al conectar a MongoDB: {e}")
    raise e

logging.basicConfig(level=logging.INFO, format="%(message)s")

def serialize_mongo_document(doc):
    """
    Convierte un documento de MongoDB en un formato serializable.
    """
    if not doc:
        return None
    doc["_id"] = str(doc["_id"])  # Convertir ObjectId a string
    return doc

@app.route('/evento/<string:event_id>', methods=['GET'])
def get_evento(event_id):
    try:
        logging.info(f"🔍 Consultando evento: {event_id}")
        # Usar directamente el método get del caché para registrar hit/miss
        cached_event = cache.get(event_id)
        
        if cached_event:
            return jsonify(cached_event)
        else:
            # Si no está en caché, buscar en MongoDB
            evento = collection.find_one({"id": event_id})
            if evento:
                evento = serialize_mongo_document(evento)
                logging.info(f"📥 Guardando en caché: {event_id} -> {evento}")
                cache.put(event_id, evento)
                return jsonify(evento)
            else:
                logging.error(f"❌ Evento no encontrado en la base de datos: {event_id}")
                return jsonify({"error": "Evento no encontrado"}), 404
    except Exception as e:
        logging.error(f"⚠️ Error procesando la solicitud para {event_id}: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@app.route('/metrics', methods=['GET'])
def metrics():
    stats = cache.get_stats()
    logging.info(f"📊 Métricas del caché: {stats}")
    return jsonify(stats)

if __name__ == '__main__':
    logging.info("🚀 Iniciando servidor de caché...")
    app.run(debug=True, host='0.0.0.0', port=5001)