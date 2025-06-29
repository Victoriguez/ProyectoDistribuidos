# ProyectoDistribuidos/mongo_exporter/export_mongo_to_tsv.py
import pymongo
import os
import csv
import json
from shapely.geometry import Point, shape
import datetime as dt_module
from datetime import timezone

# --- Configuración ---
MONGO_HOST = os.getenv('MONGO_HOST_EXPORTER', 'storage')
MONGO_PORT = int(os.getenv('MONGO_PORT_EXPORTER', '27017'))
DB_NAME_EXPORTER = os.getenv('DB_NAME_EXPORTER', 'waze_db')
COLLECTION_NAME_EXPORTER = os.getenv('COLLECTION_NAME_EXPORTER', 'eventos')
OUTPUT_TSV_PATH = os.getenv('OUTPUT_TSV_PATH_EXPORTER', '/exported_data/waze_events.tsv')
GEOJSON_FILENAME = "comunas_rm.geojson" 
GEOJSON_FILE_PATH_IN_EXPORTER_CONTAINER = os.path.join(os.getcwd(), GEOJSON_FILENAME)

# --- Variables Globales para GeoJSON ---
COMMUNAS_POLYGONS = []

# --- FUNCIONES AUXILIARES (ESTO FALTABA) ---

def load_comunas_geojson():
    """Carga los polígonos de las comunas desde el archivo GeoJSON."""
    global COMMUNAS_POLYGONS
    if COMMUNAS_POLYGONS: return

    print(f"Exporter: Intentando cargar GeoJSON desde '{GEOJSON_FILE_PATH_IN_EXPORTER_CONTAINER}'...", flush=True)
    if not os.path.exists(GEOJSON_FILE_PATH_IN_EXPORTER_CONTAINER):
        print(f"Exporter: ERROR - El archivo GeoJSON NO EXISTE en '{GEOJSON_FILE_PATH_IN_EXPORTER_CONTAINER}'", flush=True)
        return

    try:
        with open(GEOJSON_FILE_PATH_IN_EXPORTER_CONTAINER, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
        
        if geojson_data and 'features' in geojson_data:
            for feature in geojson_data['features']:
                properties = feature.get('properties', {})
                comuna_name = properties.get('Comuna', properties.get('NOM_COMUNA'))
                geom = feature.get('geometry')
                if comuna_name and geom:
                    COMMUNAS_POLYGONS.append((comuna_name, shape(geom)))
            print(f"Exporter: GeoJSON cargado. {len(COMMUNAS_POLYGONS)} polígonos procesados.", flush=True)
        else:
            print("Exporter: GeoJSON cargado pero vacío o sin 'features'.", flush=True)
    except Exception as e:
        print(f"Exporter: ERROR crítico cargando o procesando GeoJSON: {e}", flush=True)

def determine_comuna_from_geojson(lon, lat):
    """Determina la comuna para un punto (lon, lat) usando los polígonos cargados."""
    if not COMMUNAS_POLYGONS: return "COMUNA_NO_DISPONIBLE_EN_GEOJSON"
    try:
        point = Point(float(lon), float(lat))
        for comuna_name, polygon in COMMUNAS_POLYGONS:
            if polygon.contains(point):
                return comuna_name
        return "FUERA_DE_RM_CONOCIDA"
    except (ValueError, TypeError): return "COORDENADAS_INVALIDAS_PARA_COMUNA"
    except Exception: return "ERROR_EN_DET_COMUNA"

def parse_timestamp(timestamp_iso_str):
    """Parsea timestamp ISO y devuelve hora y día de la semana."""
    if not timestamp_iso_str: return None, None
    try:
        datetime_obj = dt_module.datetime.fromisoformat(timestamp_iso_str.replace("Z", "+00:00"))
        if datetime_obj.tzinfo is None: datetime_obj = datetime_obj.replace(tzinfo=timezone.utc)
        else: datetime_obj = datetime_obj.astimezone(timezone.utc)
        return datetime_obj.hour, datetime_obj.weekday()
    except: return None, None

def connect_to_mongo():
    uri = f"mongodb://{MONGO_HOST}:{MONGO_PORT}/"
    print(f"Exporter: Conectando a MongoDB en {uri}...", flush=True)
    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=10000)
        client.admin.command('ping'); db = client[DB_NAME_EXPORTER]
        return db[COLLECTION_NAME_EXPORTER]
    except Exception as e:
        print(f"Exporter: Error al conectar a MongoDB: {e}", flush=True); exit(1)

# --- FUNCIÓN PRINCIPAL ---

def main():
    print("Exporter: Iniciando script de exportación y transformación completa...", flush=True)
    load_comunas_geojson() 
    collection = connect_to_mongo()
    
    output_dir = os.path.dirname(OUTPUT_TSV_PATH)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Exporter: Exportando y transformando datos a {OUTPUT_TSV_PATH}...", flush=True)
    count = 0
    type_mapping = {
        "JAM": "CONGESTION", "ACCIDENT": "ACCIDENTE", "HAZARD": "PELIGRO_VIA",
        "ROAD_CLOSED": "CORTE_VIAL", "POLICE": "CONTROL_POLICIAL", "CONSTRUCTION": "OBRA_VIAL"
    }

    try:
        with open(OUTPUT_TSV_PATH, 'w', newline='', encoding='utf-8') as tsvfile:
            writer = csv.writer(tsvfile, delimiter='\t')
            
            # --- LÍNEA ELIMINADA ---
            # header = ['uuid', 'standardized_type', 'description', 'lon', 'lat', 'comuna', 'hora_del_dia', 'dia_semana', 'timestamp_original_iso']
            # writer.writerow(header) # <--- YA NO ESCRIBIMOS CABECERA

            for doc in collection.find({}):
                # ... (resto de la lógica de main() como estaba, sin cambios) ...
                loc_x = doc.get('location', {}).get('x')
                loc_y = doc.get('location', {}).get('y')
                timestamp_waze = doc.get('timestamp_waze', '')
                original_waze_type = doc.get('type', 'UNKNOWN')

                comuna_asignada = determine_comuna_from_geojson(loc_x, loc_y) if loc_x is not None and loc_y is not None else "DESCONOCIDA"
                hora_del_dia, dia_semana = parse_timestamp(timestamp_waze)
                standardized_type = type_mapping.get(original_waze_type, 'OTRO')
                
                if not doc.get('uuid_waze') or not loc_x or not loc_y or not timestamp_waze or comuna_asignada in ["COORDENADAS_INVALIDAS_PARA_COMUNA", "ERROR_EN_DET_COMUNA", "FUERA_DE_RM_CONOCIDA", "COMUNA_NO_DISPONIBLE_EN_GEOJSON", "DESCONOCIDA"]:
                    continue

                row = [
                    doc.get('uuid_waze', ''),
                    standardized_type,
                    doc.get('description', ''),
                    loc_x, loc_y,
                    comuna_asignada,
                    hora_del_dia if hora_del_dia is not None else '',
                    dia_semana if dia_semana is not None else '',
                    timestamp_waze
                ]
                writer.writerow(row)
                count += 1
        print(f"Exporter: Exportación completada. {count} documentos válidos escritos.", flush=True)
    except Exception as e:
        print(f"Exporter: Error durante la escritura del archivo TSV: {e}", flush=True)
        exit(1)

if __name__ == "__main__":
    main()