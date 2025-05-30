import requests
import time
from pymongo import MongoClient, UpdateOne # Importar UpdateOne
from pymongo.errors import ServerSelectionTimeoutError, BulkWriteError # Importar BulkWriteError
from datetime import datetime, timezone
import os

# --- Configuración de MongoDB ---
MONGO_HOST = os.getenv('MONGO_HOST', 'storage') # Nombre del servicio MongoDB en docker-compose
MONGO_PORT = int(os.getenv('MONGO_PORT', '27017'))
DB_NAME_SCRAPER = os.getenv('DB_NAME_SCRAPER', 'waze_db')
COLLECTION_NAME_SCRAPER = os.getenv('COLLECTION_NAME_SCRAPER', 'eventos')

MONGO_URI_SCRAPER = f"mongodb://{MONGO_HOST}:{MONGO_PORT}/"

def conectar_mongo():
    print(f"Scraper: Conectando a MongoDB en {MONGO_URI_SCRAPER}...", flush=True)
    intentos_conexion = 5
    for i in range(intentos_conexion):
        try:
            client = MongoClient(MONGO_URI_SCRAPER, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            print("Scraper: Conexión exitosa a MongoDB.", flush=True)
            db = client[DB_NAME_SCRAPER]
            return db[COLLECTION_NAME_SCRAPER]
        except ServerSelectionTimeoutError as e:
            print(f"Scraper: No se pudo conectar a MongoDB (intento {i+1}/{intentos_conexion}): {e}. Reintentando en 5 segundos...", flush=True)
            if i < intentos_conexion - 1:
                time.sleep(5)
            else:
                print("Scraper: Se superaron los intentos de conexión a MongoDB. Saliendo.", flush=True)
                exit(1) # Salir si no se puede conectar
        except Exception as e: # Capturar otras posibles excepciones de MongoClient
            print(f"Scraper: Error inesperado al conectar a MongoDB (intento {i+1}/{intentos_conexion}): {e}. Saliendo.", flush=True)
            exit(1) # Salir si no se puede conectar


# --- Configuración de Waze API ---
TOP = os.getenv('WAZE_TOP', -33.3)
BOTTOM = os.getenv('WAZE_BOTTOM', -33.7)
LEFT = os.getenv('WAZE_LEFT', -70.9)
RIGHT = os.getenv('WAZE_RIGHT', -70.5)
TYPES = 'alerts' # Enfocarnos en alertas
URL = f"https://www.waze.com/live-map/api/georss?top={TOP}&bottom={BOTTOM}&left={LEFT}&right={RIGHT}&env=row&types={TYPES}"

def obtener_datos_waze():
    print(f"Scraper: Consultando Waze Live Map API: {URL}", flush=True)
    try:
        response = requests.get(URL, timeout=15) # Aumentar un poco el timeout
        response.raise_for_status()
        data = response.json()
        print(f"Scraper: Datos recibidos de Waze. {len(data.get('alerts', []))} alertas encontradas.", flush=True)
        return data
    except requests.exceptions.HTTPError as http_err:
        print(f"Scraper: Error HTTP al consultar Waze: {http_err} - {response.text[:200]}", flush=True)
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Scraper: Error de conexión al consultar Waze: {conn_err}", flush=True)
    except requests.exceptions.Timeout as timeout_err:
        print(f"Scraper: Timeout al consultar Waze: {timeout_err}", flush=True)
    except requests.exceptions.RequestException as req_err:
        print(f"Scraper: Error en la solicitud a Waze: {req_err}", flush=True)
    except ValueError as json_err:
        print(f"Scraper: Error al decodificar JSON de Waze: {json_err} - Respuesta: {response.text[:200]}", flush=True)
    return None

def procesar_y_guardar_alertas(coleccion, data):
    if not data or 'alerts' not in data:
        print("Scraper: No hay sección 'alerts' en los datos o datos vacíos.", flush=True)
        return 0

    alertas_waze = data.get('alerts', [])
    if not alertas_waze:
        print("Scraper: No hay alertas para procesar.", flush=True)
        return 0

    operaciones_bulk = []
    alertas_procesadas_count = 0

    for alerta_raw in alertas_waze:
        # --- EXTRACCIÓN DE CAMPOS AJUSTADA A TU JSON ---
        
        uuid_alerta = alerta_raw.get('uuid') # ID ÚNICO
        if not uuid_alerta:
            print(f"Scraper: Alerta sin UUID, omitiendo: {alerta_raw.get('location')}", flush=True)
            continue

        tipo_alerta = alerta_raw.get('type', 'UNKNOWN') # TIPO DE ALERTA
        subtipo_alerta = alerta_raw.get('subtype', None) # SUBTIPO
        
        # DESCRIPCIÓN: Construirla a partir de 'street' y 'additionalInfo'
        street_info = alerta_raw.get('street', '')
        additional_info = alerta_raw.get('additionalInfo', '')
        descripcion = street_info
        if additional_info:
            if descripcion: # Si ya hay street_info, añadir additional_info
                descripcion += f" ({additional_info})"
            else: # Si no hay street_info, usar solo additional_info
                descripcion = additional_info
        if not descripcion: # Si ambos están vacíos
            descripcion = "Sin descripción detallada"
        
        location_data = alerta_raw.get('location')
        if not location_data or not isinstance(location_data, dict) or 'x' not in location_data or 'y' not in location_data:
            print(f"Scraper: Alerta {uuid_alerta} sin datos de ubicación válidos, omitiendo.", flush=True)
            continue

        pub_millis = alerta_raw.get('pubMillis')
        timestamp_waze_iso = None
        if pub_millis:
            try:
                timestamp_dt = datetime.fromtimestamp(pub_millis / 1000, tz=timezone.utc)
                timestamp_waze_iso = timestamp_dt.isoformat()
            except Exception as e:
                print(f"Scraper: Error convirtiendo pubMillis para alerta {uuid_alerta}: {e}", flush=True)
        
        documento_alerta = {
            'uuid_waze': uuid_alerta,       # ID único de Waze
            'type': tipo_alerta,            # Tipo de alerta (JAM, HAZARD, POLICE, etc.)
            'subtype': subtipo_alerta,      # Subtipo (HAZARD_ON_ROAD_POT_HOLE, etc.)
            'description': descripcion,     # Descripción construida
            'location': {
                'x': location_data['x'],    # Longitud
                'y': location_data['y']     # Latitud
            },
            'timestamp_waze': timestamp_waze_iso, # Timestamp del evento de Waze en ISO UTC
            'timestamp_processed_scraper': datetime.now(timezone.utc).isoformat(),
            # 'raw_waze_data': alerta_raw # Opcional: guardar toda la data cruda para referencia futura
        }
        
        operaciones_bulk.append(
            UpdateOne(
                {'uuid_waze': uuid_alerta}, # Filtro para encontrar el documento
                {'$set': documento_alerta}, # Datos a establecer/actualizar
                upsert=True                 # Crear si no existe
            )
        )
        alertas_procesadas_count += 1

    if operaciones_bulk:
        try:
            print(f"Scraper: Realizando bulk write de {len(operaciones_bulk)} operaciones en MongoDB...", flush=True)
            result = coleccion.bulk_write(operaciones_bulk)
            print(f"Scraper: Bulk write completado. Insertados(upserted): {result.upserted_count}, Modificados: {result.modified_count}, Coincidentes: {result.matched_count}", flush=True)
        except BulkWriteError as bwe:
            print(f"Scraper: Error en bulk write: {bwe.details}", flush=True)
        except Exception as e:
            print(f"Scraper: Error inesperado durante bulk write: {e}", flush=True)
    
    return alertas_procesadas_count

if __name__ == '__main__':
    print("Scraper (v2 - con tipo y descripción) iniciado.", flush=True)
    coleccion_eventos = conectar_mongo()
    
    intervalo_scrapeo_segundos = int(os.getenv('SCRAPE_INTERVAL_SECONDS', 300))
    max_eventos_a_recolectar = int(os.getenv('MAX_EVENTS_TO_COLLECT', 10000)) 
    eventos_recolectados_actualmente_en_db = 0

    try:
        eventos_recolectados_actualmente_en_db = coleccion_eventos.count_documents({})
        print(f"Scraper: Eventos existentes en DB: {eventos_recolectados_actualmente_en_db}", flush=True)

        # Si ya se alcanzó el límite, no hacer nada más.
        if eventos_recolectados_actualmente_en_db >= max_eventos_a_recolectar:
            print(f"Scraper: Límite de {max_eventos_a_recolectar} eventos ya alcanzado o superado. Saliendo.", flush=True)
        else:
            while eventos_recolectados_actualmente_en_db < max_eventos_a_recolectar:
                datos_waze_actuales = obtener_datos_waze()
                if datos_waze_actuales:
                    procesar_y_guardar_alertas(coleccion_eventos, datos_waze_actuales)
                    eventos_recolectados_actualmente_en_db = coleccion_eventos.count_documents({}) # Recontar
                    print(f"Scraper: Total de eventos en DB ahora: {eventos_recolectados_actualmente_en_db}", flush=True)

                if eventos_recolectados_actualmente_en_db >= max_eventos_a_recolectar:
                    print(f"Scraper: Se alcanzó el límite de {max_eventos_a_recolectar} eventos.", flush=True)
                    break
                
                print(f"Scraper: Esperando {intervalo_scrapeo_segundos} segundos para el próximo ciclo...", flush=True)
                time.sleep(intervalo_scrapeo_segundos)
                
    except KeyboardInterrupt:
        print("Scraper: Interrupción por teclado recibida. Saliendo...", flush=True)
    finally:
        if coleccion_eventos is not None and coleccion_eventos.database.client is not None:
             coleccion_eventos.database.client.close() # Cerrar la conexión al cliente MongoDB
             print("Scraper: Conexión a MongoDB cerrada.")
        print(f"Scraper finalizado. Total de eventos en la base de datos: {eventos_recolectados_actualmente_en_db}", flush=True)