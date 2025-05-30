import pymongo
import datetime # Importa el módulo datetime
from datetime import timezone # Importa timezone específicamente para datetime.timezone.utc
import os
import json
from shapely.geometry import Point, shape

# --- Configuración ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

DB_NAME = os.getenv("DB_NAME", "waze_db") 
RAW_COLLECTION_NAME = os.getenv("RAW_COLLECTION_NAME", "eventos")

# Para prueba local (ASEGÚRATE QUE ESTA LÍNEA ESTÉ ACTIVA PARA PROBAR):
OUTPUT_FILE_PATH = os.getenv("OUTPUT_FILE_PATH", "./cleaned_events_test.tsv") 
# Para Docker (COMENTA ESTA LÍNEA CUANDO PRUEBES LOCALMENTE):
# OUTPUT_FILE_PATH = os.getenv("OUTPUT_FILE_PATH", "/app_output/cleaned_events.tsv") 

GEOJSON_COMUNAS_PATH = "comunas_rm.geojson" 

def connect_to_mongo():
    if os.getenv('DOCKER_ENV'):
        effective_mongo_uri = f"mongodb://{os.getenv('MONGO_SERVICE_NAME', 'mongo_db')}:27017/"
    else:
        effective_mongo_uri = MONGO_URI

    try:
        client = pymongo.MongoClient(effective_mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print(f"Filter: Conexión a MongoDB ({effective_mongo_uri}) exitosa.")
        return client
    except Exception as e:
        print(f"Filter: Error al conectar a MongoDB ({effective_mongo_uri}): {e}")
        return None

def get_raw_events(client):
    if not client: return []
    db = client[DB_NAME]
    collection = db[RAW_COLLECTION_NAME]
    events = list(collection.find({}))
    print(f"Filter: Se encontraron {len(events)} eventos crudos en DB: '{DB_NAME}', Colección: '{RAW_COLLECTION_NAME}'.")
    return events

def determine_comuna(lon, lat, comunas_geojson_data):
    if comunas_geojson_data is None: return "COMUNA_GEOJSON_NO_DISPONIBLE"
    try: point = Point(float(lon), float(lat))
    except (ValueError, TypeError): return "COORDENADAS_INVALIDAS"
    for feature in comunas_geojson_data.get('features', []):
        geom = feature.get('geometry')
        if not geom: continue
        try: polygon = shape(geom)
        except Exception: continue 
        if polygon.contains(point):
            return feature.get('properties', {}).get('Comuna', 'COMUNA_SIN_NOMBRE_EN_PROPS')
    return "FUERA_DE_COMUNAS_RM"

def process_event(event_doc, comunas_data):
    processed_event = {}

    processed_event['id'] = event_doc.get('uuid_waze', str(event_doc.get('_id')))
    original_type = event_doc.get('type', 'UNKNOWN').upper() 
    processed_event['original_type'] = original_type
    
    type_mapping = {
        "JAM": "CONGESTION", "ACCIDENT": "ACCIDENTE",
        "HAZARD": "PELIGRO_VIA", "ROAD_CLOSED": "CORTE_VIAL",
        "POLICE": "CONTROL_POLICIAL", "CONSTRUCTION": "OBRA_VIAL",
    }
    processed_event['standardized_type'] = type_mapping.get(original_type, 'OTRO')

    location_data = event_doc.get('location')
    lon_val, lat_val = None, None
    if location_data and isinstance(location_data, dict):
        lon_val = location_data.get('x')
        lat_val = location_data.get('y')

    if lon_val is not None and lat_val is not None:
        processed_event['lon'] = lon_val
        processed_event['lat'] = lat_val
        processed_event['comuna'] = determine_comuna(lon_val, lat_val, comunas_data)
    else:
        processed_event['lon'] = None; processed_event['lat'] = None
        processed_event['comuna'] = "UBICACION_DESCONOCIDA"

    timestamp_iso_waze = event_doc.get('timestamp_waze')
    if timestamp_iso_waze:
        try:
            # CORRECCIÓN: Llamar a fromisoformat desde datetime.datetime
            dt_object = datetime.datetime.fromisoformat(timestamp_iso_waze.replace("Z", "+00:00"))
            
            if dt_object.tzinfo is None or dt_object.tzinfo.utcoffset(dt_object) is None:
                dt_object = dt_object.replace(tzinfo=timezone.utc) # datetime.timezone.utc
            else:
                dt_object = dt_object.astimezone(timezone.utc) # datetime.timezone.utc

            processed_event['timestamp_iso'] = dt_object.isoformat() 
            processed_event['hora_del_dia'] = dt_object.hour
            processed_event['dia_semana'] = dt_object.weekday()
        except ValueError as e: 
            print(f"Filter: Error parseando timestamp '{timestamp_iso_waze}': {e}")
            processed_event['timestamp_iso'] = timestamp_iso_waze 
            processed_event['hora_del_dia'] = None; processed_event['dia_semana'] = None
        except Exception as e_gen:
            print(f"Filter: Error general parseando timestamp '{timestamp_iso_waze}': {e_gen}")
            processed_event['timestamp_iso'] = timestamp_iso_waze
            processed_event['hora_del_dia'] = None; processed_event['dia_semana'] = None
    else:
        processed_event['timestamp_iso'] = None
        processed_event['hora_del_dia'] = None; processed_event['dia_semana'] = None
    
    processed_event['description'] = str(event_doc.get('description', 'SIN_DESCRIPCION'))

    if processed_event['lon'] is None or original_type == 'UNKNOWN':
        return None 

    return processed_event

def save_cleaned_data_tsv(cleaned_events, filepath):
    output_dir = os.path.dirname(filepath)
    if output_dir and not os.path.exists(output_dir) :
        os.makedirs(output_dir, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        headers = ['id', 'timestamp_iso', 'lat', 'lon', 'standardized_type', 'comuna', 'description', 'hora_del_dia', 'dia_semana']
        f.write('\t'.join(headers) + '\n')
        for event_data in cleaned_events:
            row_values = [
                str(event_data.get('id', '')), str(event_data.get('timestamp_iso', '')),
                str(event_data.get('lat', '')), str(event_data.get('lon', '')),
                str(event_data.get('standardized_type', '')), str(event_data.get('comuna', '')),
                str(event_data.get('description', '')).replace('\t', ' ').replace('\n', ' '),
                str(event_data.get('hora_del_dia', '')), str(event_data.get('dia_semana', ''))
            ]
            f.write('\t'.join(row_values) + '\n')
    print(f"Filter: Datos limpios guardados en {filepath}")

def main():
    mongo_client = connect_to_mongo()
    if not mongo_client: return

    raw_events_data = get_raw_events(mongo_client)
    if not raw_events_data:
        print("Filter: No hay eventos crudos para procesar."); mongo_client.close(); return

    comunas_geojson = None
    script_dir = os.path.dirname(os.path.abspath(__file__))
    geojson_full_path = os.path.join(script_dir, GEOJSON_COMUNAS_PATH)
    try:
        with open(geojson_full_path, 'r', encoding='utf-8') as f:
            comunas_geojson = json.load(f)
        print(f"Filter: GeoJSON de comunas cargado desde {geojson_full_path}")
    except FileNotFoundError: print(f"Filter: ERROR - Archivo GeoJSON no encontrado en {geojson_full_path}.")
    except json.JSONDecodeError: print(f"Filter: ERROR - Error al decodificar GeoJSON en {geojson_full_path}.")

    cleaned_events_list = []
    for raw_event_doc in raw_events_data:
        processed = process_event(raw_event_doc, comunas_geojson) 
        if processed:
            cleaned_events_list.append(processed)
    
    print(f"Filter: Procesados {len(cleaned_events_list)} eventos válidos de {len(raw_events_data)} eventos crudos.")

    if cleaned_events_list:
        save_cleaned_data_tsv(cleaned_events_list, OUTPUT_FILE_PATH)

    mongo_client.close()
    print("Filter: Proceso de filtrado y homogeneización completado.")

if __name__ == "__main__":
    main()