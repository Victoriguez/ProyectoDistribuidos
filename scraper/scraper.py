import requests
import time
from pymongo import MongoClient, UpdateOne
from pymongo.errors import ServerSelectionTimeoutError, BulkWriteError
from datetime import datetime, timezone
import os
import sys # Importar sys para salir explícitamente

# --- Configuración ---
MONGO_HOST = os.getenv('MONGO_HOST', 'storage')
# La siguiente línea estaba en tu docker-compose, así que la usamos en el script.
MAX_EVENTS_TO_COLLECT = int(os.getenv('MAX_EVENTS_TO_COLLECT', 200)) 

MONGO_URI_SCRAPER = f"mongodb://{MONGO_HOST}:27017/"

def connect_to_mongo():
    print(f"Scraper: Conectando a MongoDB en {MONGO_URI_SCRAPER}...", flush=True)
    for attempt in range(5):
        try:
            client = MongoClient(MONGO_URI_SCRAPER, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            print("Scraper: Conexión exitosa a MongoDB.", flush=True)
            return client['waze_db']['eventos']
        except Exception as e:
            print(f"Scraper: No se pudo conectar (intento {attempt + 1}/5): {e}. Reintentando...", flush=True)
            time.sleep(5)
    print("Scraper: Se superaron los intentos de conexión a MongoDB. Saliendo.", flush=True)
    sys.exit(1) # Salir con código de error

# ... (obtener_datos_waze, procesar_y_guardar_alertas como las tenías) ...

def obtener_datos_waze():
    URL = f"https://www.waze.com/live-map/api/georss?top=-33.3&bottom=-33.7&left=-70.9&right=-70.5&env=row&types=alerts"
    print(f"Scraper: Consultando Waze API...", flush=True)
    try:
        response = requests.get(URL, timeout=15); response.raise_for_status()
        data = response.json()
        print(f"Scraper: Datos recibidos. {len(data.get('alerts', []))} alertas encontradas.", flush=True)
        return data
    except Exception as e:
        print(f"Scraper: Error en la solicitud a Waze: {e}", flush=True)
    return None

def procesar_y_guardar_alertas(coleccion, data):
    if not data or 'alerts' not in data: return 0
    alertas_waze = data.get('alerts', []);
    if not alertas_waze: return 0
    operaciones_bulk = []
    for alerta_raw in alertas_waze:
        uuid_alerta = alerta_raw.get('uuid')
        if not uuid_alerta: continue
        # ... (resto de la lógica de procesar_y_guardar_alertas que ya tienes) ...
        tipo_alerta = alerta_raw.get('type', 'UNKNOWN'); subtipo_alerta = alerta_raw.get('subtype')
        street_info = alerta_raw.get('street', ''); additional_info = alerta_raw.get('additionalInfo', '')
        descripcion = street_info;
        if additional_info: descripcion = f"{street_info} ({additional_info})" if street_info else additional_info
        if not descripcion: descripcion = "Sin descripción detallada"
        location_data = alerta_raw.get('location')
        if not location_data: continue
        pub_millis = alerta_raw.get('pubMillis')
        timestamp_iso = datetime.fromtimestamp(pub_millis / 1000, tz=timezone.utc).isoformat() if pub_millis else None
        documento_alerta = {
            'uuid_waze': uuid_alerta, 'type': tipo_alerta, 'subtype': subtipo_alerta, 'description': descripcion,
            'location': {'x': location_data.get('x'), 'y': location_data.get('y')},
            'timestamp_waze': timestamp_iso, 'timestamp_processed_scraper': datetime.now(timezone.utc).isoformat()
        }
        operaciones_bulk.append(UpdateOne({'uuid_waze': uuid_alerta}, {'$set': documento_alerta}, upsert=True))
    if operaciones_bulk:
        try:
            result = coleccion.bulk_write(operaciones_bulk)
            print(f"Scraper: Bulk write completado. Upserted: {result.upserted_count}, Modified: {result.modified_count}", flush=True)
            return result.upserted_count # Devolver solo los nuevos insertados para el conteo
        except BulkWriteError as bwe: print(f"Scraper: Error en bulk write: {bwe.details}", flush=True)
    return 0

# --- Bucle Principal Corregido ---
if __name__ == '__main__':
    print("Scraper (v3 - con finalización explícita) iniciado.", flush=True)
    coleccion_eventos = connect_to_mongo()
    
    # Limpiar la colección antes de empezar, para asegurar un conteo limpio
    print(f"Scraper: Limpiando colección '{coleccion_eventos.name}'...", flush=True)
    coleccion_eventos.delete_many({})

    eventos_recolectados_total = 0
    try:
        while eventos_recolectados_total < MAX_EVENTS_TO_COLLECT:
            print(f"\nScraper: Ciclo de recolección. Total actual: {eventos_recolectados_total}/{MAX_EVENTS_TO_COLLECT}", flush=True)
            datos_waze_actuales = obtener_datos_waze()
            if datos_waze_actuales:
                nuevos_eventos = procesar_y_guardar_alertas(coleccion_eventos, datos_waze_actuales)
                eventos_recolectados_total += nuevos_eventos
            else:
                print("Scraper: No se obtuvieron datos en este ciclo.", flush=True)
            
            if eventos_recolectados_total < MAX_EVENTS_TO_COLLECT:
                print("Scraper: Esperando 60 segundos para el próximo ciclo...", flush=True)
                time.sleep(60) # Esperar un tiempo razonable entre llamadas a la API

        print(f"Scraper: Límite de {MAX_EVENTS_TO_COLLECT} eventos alcanzado. Finalizando.", flush=True)

    except KeyboardInterrupt:
        print("Scraper: Interrupción por teclado recibida. Saliendo...", flush=True)
    finally:
        if coleccion_eventos is not None and coleccion_eventos.database.client is not None:
             coleccion_eventos.database.client.close() 
             print("Scraper: Conexión a MongoDB cerrada.", flush=True)
    
    print("Scraper finalizado.", flush=True)
    sys.exit(0) # Salir explícitamente con código 0