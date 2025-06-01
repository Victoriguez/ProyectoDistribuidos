# ProyectoDistribuidos/mongo_exporter/export_mongo_to_tsv.py
import pymongo
import os
import csv
import json
from shapely.geometry import Point, shape # Para la lógica geoespacial
import datetime as dt_module # Usar alias para datetime
from datetime import timezone # Para UTC

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

def load_comunas_geojson():
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
                comuna_name = properties.get('Comuna', properties.get('NOM_COMUNA')) # Ajusta según tu GeoJSON
                geom = feature.get('geometry')
                if comuna_name and geom:
                    COMMUNAS_POLYGONS.append((comuna_name, shape(geom)))
            print(f"Exporter: GeoJSON cargado. {len(COMMUNAS_POLYGONS)} polígonos de comunas procesados.", flush=True)
        else:
            print("Exporter: GeoJSON cargado pero vacío o sin 'features'.", flush=True)
    except Exception as e:
        print(f"Exporter: ERROR crítico cargando o procesando GeoJSON: {e}", flush=True)

def determine_comuna_from_geojson(lon, lat):
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
    if not timestamp_iso_str:
        return None, None
    try:
        # El timestamp_waze ya viene como 'YYYY-MM-DDTHH:MM:SS+00:00'
        datetime_obj = dt_module.datetime.fromisoformat(timestamp_iso_str.replace("Z", "+00:00"))
        # Asegurar que es UTC si no tiene timezone explícita (aunque el nuestro ya lo tiene)
        if datetime_obj.tzinfo is None or datetime_obj.tzinfo.utcoffset(datetime_obj) is None:
            datetime_obj = datetime_obj.replace(tzinfo=timezone.utc)
        else: # Asegurar que sea UTC
            datetime_obj = datetime_obj.astimezone(timezone.utc)
        
        return datetime_obj.hour, datetime_obj.weekday() # Lunes=0, Domingo=6
    except ValueError:
        # print(f"Exporter: Error de ValueError parseando timestamp '{timestamp_iso_str}'")
        return None, None
    except Exception: # Captura general
        # print(f"Exporter: Error general parseando timestamp '{timestamp_iso_str}'")
        return None, None

def connect_to_mongo():
    uri = f"mongodb://{MONGO_HOST}:{MONGO_PORT}/"
    print(f"Exporter: Conectando a MongoDB en {uri}...", flush=True)
    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=10000)
        client.admin.command('ping'); db = client[DB_NAME_EXPORTER]
        return db[COLLECTION_NAME_EXPORTER]
    except Exception as e:
        print(f"Exporter: Error al conectar a MongoDB: {e}", flush=True); exit(1)

def main():
    print("Exporter: Iniciando script de exportación (con comuna y partes de tiempo)...", flush=True)
    load_comunas_geojson() 
    collection = connect_to_mongo()
    
    # Campos que queremos extraer y el orden en el TSV
    # uuid_waze, type, subtype, description, location_x, location_y, timestamp_waze, comuna, hora_del_dia, dia_semana
    
    output_dir = os.path.dirname(OUTPUT_TSV_PATH)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir); print(f"Exporter: Creado directorio de salida {output_dir}", flush=True)

    print(f"Exporter: Exportando datos a {OUTPUT_TSV_PATH}...", flush=True)
    count = 0
    try:
        with open(OUTPUT_TSV_PATH, 'w', newline='', encoding='utf-8') as tsvfile:
            writer = csv.writer(tsvfile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            
            for doc in collection.find({}):
                count += 1
                loc_x = doc.get('location', {}).get('x')
                loc_y = doc.get('location', {}).get('y')
                timestamp_waze = doc.get('timestamp_waze', '')
                
                comuna_asignada = "DESCONOCIDA" # Default si no se puede determinar
                if loc_x is not None and loc_y is not None:
                    comuna_asignada = determine_comuna_from_geojson(loc_x, loc_y)
                
                hora_del_dia, dia_semana = parse_timestamp(timestamp_waze)
                
                row = [
                    doc.get('uuid_waze', ''),
                    doc.get('type', ''),
                    doc.get('subtype', ''),
                    doc.get('description', ''),
                    loc_x if loc_x is not None else '',
                    loc_y if loc_y is not None else '',
                    timestamp_waze,
                    comuna_asignada,
                    hora_del_dia if hora_del_dia is not None else '', # Escribir vacío si es None
                    dia_semana if dia_semana is not None else ''    # Escribir vacío si es None
                ]
                writer.writerow(row)
        print(f"Exporter: Exportación completada. {count} documentos escritos.", flush=True)
    except Exception as e:
        print(f"Exporter: Error durante la escritura del archivo TSV: {e}", flush=True); exit(1)

if __name__ == "__main__":
    main()