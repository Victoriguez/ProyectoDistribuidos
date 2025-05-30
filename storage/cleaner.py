from pymongo import MongoClient
from datetime import datetime
import pytz
import time
from pymongo.errors import ServerSelectionTimeoutError

def esperar_mongo(client, intentos=10, intervalo=3):
    for i in range(intentos):
        try:
            client.admin.command("ping")
            print("Mongo está listo.")
            return
        except ServerSelectionTimeoutError:
            print(f"Esperando a Mongo... intento {i+1}/{intentos}")
            time.sleep(intervalo)
    raise Exception("No se pudo conectar a Mongo luego de varios intentos.")

client = MongoClient("mongodb://mongo-storage:27017")
esperar_mongo(client)
db = client["waze_db"]
coleccion = db["eventos"]

def es_valido(evento):
    campos_obligatorios = ["location", "speed", "mood"]
    for campo in campos_obligatorios:
        if campo not in evento or evento[campo] in [None, "", {}]:
            return False
    if not isinstance(evento.get("location"), dict):
        return False
    if not isinstance(evento.get("speed"), (int, float)):
        return False
    return True

def limpiar_eventos():
    total = coleccion.count_documents({})
    print(f"Eventos totales antes de limpieza: {total}")
    cursor = coleccion.find({})
    eliminados = 0
    actualizados = 0

    for evento in cursor:
        _id = evento["_id"]

        if not es_valido(evento):
            coleccion.delete_one({"_id": _id})
            eliminados += 1
            continue

        if "timestamp" in evento and isinstance(evento["timestamp"], str):
            try:
                timestamp = datetime.fromisoformat(evento["timestamp"])
                timestamp = timestamp.astimezone(pytz.UTC)
                coleccion.update_one(
                    {"_id": _id},
                    {"$set": {"timestamp": timestamp}}
                )
                actualizados += 1
            except Exception as e:
                print(f"Error al convertir fecha en {_id}: {e}")
                coleccion.delete_one({"_id": _id})
                eliminados += 1

    print(f"Eventos eliminados: {eliminados}")
    print(f"Eventos con fecha normalizada: {actualizados}")
    restantes = coleccion.count_documents({})
    print(f"Eventos totales después de limpieza: {restantes}")

if __name__ == "__main__":
    limpiar_eventos()
