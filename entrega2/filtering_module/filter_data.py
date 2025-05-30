import pymongo
import datetime
import os
import json
from shapely.geometry import Point, shape # <--- IMPORTACIÓN CLAVE

# --- Configuración ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "proyecto_distribuidos_db")
RAW_COLLECTION_NAME = os.getenv("RAW_COLLECTION_NAME", "waze_alerts")

# Para prueba local, puedes cambiar esto temporalmente:
OUTPUT_FILE_PATH = os.getenv("OUTPUT_FILE_PATH", "./cleaned_events_test.tsv") 
# OUTPUT_FILE_PATH = os.getenv("OUTPUT_FILE_PATH", "/app_output/cleaned_events.tsv") 

# Asegúrate que este archivo exista en la misma carpeta que filter_data.py
# o ajusta la ruta si lo guardaste en otro lugar dentro de filtering_module/
GEOJSON_COMUNAS_PATH = "comunas_rm.geojson" 

def connect_to_mongo():
    """Conecta a MongoDB y devuelve el cliente."""
    try:
        client = pymongo.MongoClient(MONGO_URI)
        client.admin.command('ping') # Verificar conexión
        print("Conexión a MongoDB exitosa.")
        return client
    except Exception as e:
        print(f"Error al conectar a MongoDB: {e}")
        return None

def get_raw_events(client):
    """Obtiene todos los eventos crudos de la colección."""
    if not client:
        return []
    db = client[DB_NAME]
    collection = db[RAW_COLLECTION_NAME]
    events = list(collection.find({}))
    print(f"Se encontraron {len(events)} eventos crudos.")
    return events

def determine_comuna(lon, lat, comunas_geojson_data):
    """
    Determina la comuna para un punto (lon, lat) dado.
    Usa shapely y los datos del GeoJSON.
    """
    if comunas_geojson_data is None:
        return "COMUNA_GEOJSON_NO_DISPONIBLE"

    try:
        # Asegurarse de que lon y lat sean floats válidos
        point = Point(float(lon), float(lat))
    except (ValueError, TypeError):
        return "COORDENADAS_INVALIDAS"

    for feature in comunas_geojson_data.get('features', []):
        geom = feature.get('geometry')
        if not geom:
            continue

        try:
            polygon = shape(geom)
        except Exception:
            # Opcional: print(f"Error al crear polígono para feature: {e}")
            continue 

        if polygon.contains(point):
            # Basado en tu GeoJSON, la propiedad es "Comuna".
            return feature.get('properties', {}).get('Comuna', 'COMUNA_SIN_NOMBRE_EN_PROPS')

    return "FUERA_DE_COMUNAS_RM"

def process_event(event, comunas_data): # 'comunas_data' es el GeoJSON parseado
    """Limpia, estandariza y enriquece un solo evento."""
    processed_event = {}

    processed_event['id'] = str(event.get('_id', 'N/A'))
    original_type = event.get('type', 'UNKNOWN')
    processed_event['original_type'] = original_type
    
    type_mapping = {
        "ACCIDENT": "ACCIDENTE",
        "JAM": "CONGESTION",
        "ROAD_CLOSED": "CORTE_VIAL",
        "HAZARD": "PELIGRO_VIA",
        # Añade más mapeos según los tipos de Waze que encuentres
    }
    processed_event['standardized_type'] = type_mapping.get(original_type, 'OTRO')

    location = event.get('location')
    if location and 'x' in location and 'y' in location:
        lon_val = location['x']
        lat_val = location['y']
        processed_event['lon'] = lon_val
        processed_event['lat'] = lat_val
        # Llamada a determine_comuna con los datos GeoJSON cargados
        processed_event['comuna'] = determine_comuna(lon_val, lat_val, comunas_data)
    else:
        processed_event['lon'] = None
        processed_event['lat'] = None
        processed_event['comuna'] = "UBICACION_DESCONOCIDA"

    pub_millis = event.get('pubMillis')
    if pub_millis:
        try:
            # Asegurarse que pub_millis sea un número antes de dividir
            dt_object = datetime.datetime.fromtimestamp(float(pub_millis) / 1000, tz=datetime.timezone.utc)
            processed_event['timestamp_iso'] = dt_object.isoformat()
            processed_event['hora_del_dia'] = dt_object.hour
            processed_event['dia_semana'] = dt_object.weekday() # Lunes=0, Domingo=6
        except (ValueError, TypeError):
            processed_event['timestamp_iso'] = None
            processed_event['hora_del_dia'] = None
            processed_event['dia_semana'] = None
    else:
        processed_event['timestamp_iso'] = None
        processed_event['hora_del_dia'] = None
        processed_event['dia_semana'] = None
    
    processed_event['description'] = str(event.get('description', '')) # Asegurar que sea string

    # Filtro básico: si no hay ubicación válida o tipo original es desconocido, descartar
    if processed_event['lon'] is None or original_type == 'UNKNOWN':
        return None 

    return processed_event

def save_cleaned_data_tsv(cleaned_events, filepath):
    """Guarda los datos limpios en formato TSV."""
    # Asegurarse de que el directorio de salida exista
    # Esto es más relevante cuando se ejecuta dentro de Docker y el path es absoluto
    output_dir = os.path.dirname(filepath)
    if output_dir: # Solo crear si no es el directorio actual
        os.makedirs(output_dir, exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        headers = ['id', 'timestamp_iso', 'lat', 'lon', 'standardized_type', 'comuna', 'description', 'hora_del_dia', 'dia_semana']
        f.write('\t'.join(headers) + '\n')
        
        for event in cleaned_events:
            # Solo procesar si el evento no es None (ya filtrado en la lista)
            row_values = [
                str(event.get('id', '')),
                str(event.get('timestamp_iso', '')),
                str(event.get('lat', '')),
                str(event.get('lon', '')),
                str(event.get('standardized_type', '')),
                str(event.get('comuna', '')),
                str(event.get('description', '')).replace('\t', ' ').replace('\n', ' '),
                str(event.get('hora_del_dia', '')),
                str(event.get('dia_semana', ''))
            ]
            f.write('\t'.join(row_values) + '\n')
    print(f"Datos limpios guardados en {filepath}")

def main():
    mongo_client = connect_to_mongo()
    if not mongo_client:
        return

    raw_events_data = get_raw_events(mongo_client)
    if not raw_events_data:
        print("No hay eventos crudos para procesar.")
        mongo_client.close()
        return

    comunas_geojson = None
    # Construir el path al GeoJSON relativo a la ubicación de este script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    geojson_full_path = os.path.join(script_dir, GEOJSON_COMUNAS_PATH)

    try:
        with open(geojson_full_path, 'r', encoding='utf-8') as f:
            comunas_geojson = json.load(f)
        print(f"GeoJSON de comunas cargado desde {geojson_full_path}")
    except FileNotFoundError:
        print(f"ERROR: Archivo GeoJSON de comunas no encontrado en {geojson_full_path}. No se podrá determinar la comuna.")
        # Decidimos continuar sin comunas si el archivo no se encuentra, 
        # la función determine_comuna retornará "COMUNA_GEOJSON_NO_DISPONIBLE"
    except json.JSONDecodeError:
        print(f"ERROR: Error al decodificar el archivo GeoJSON de comunas {geojson_full_path}.")
        # Similar, continuamos y determine_comuna manejará comunas_geojson siendo None.

    cleaned_events_list = []
    for raw_event in raw_events_data:
        # Pasamos comunas_geojson (que puede ser None si falló la carga)
        processed = process_event(raw_event, comunas_geojson) 
        if processed:
            cleaned_events_list.append(processed)
    
    print(f"Procesados {len(cleaned_events_list)} eventos válidos.")

    if cleaned_events_list:
        # Para la ejecución dentro de Docker, OUTPUT_FILE_PATH es el path DENTRO del contenedor.
        # El mapeo de volúmenes en docker-compose se encarga de dónde aparece en el host.
        # Por ejemplo, si OUTPUT_FILE_PATH es "/app_output/cleaned_events.tsv"
        # y en docker-compose montas "./entrega2/pig_processing/data_input:/app_output",
        # el archivo se guardará en "./entrega2/pig_processing/data_input/cleaned_events.tsv" en tu máquina.

        # La creación de 'local_output_dir' que estaba antes era más para asegurar
        # que el directorio anfitrión existiera ANTES de que Docker intentara montar,
        # pero Docker generalmente crea el directorio anfitrión si no existe al montar un volumen.
        # Lo importante es que el script dentro del contenedor PUEDA escribir en OUTPUT_FILE_PATH.
        
        # Si OUTPUT_FILE_PATH es un path absoluto como "/app_output/...", 
        # os.makedirs(os.path.dirname(filepath), exist_ok=True) dentro de save_cleaned_data_tsv
        # se encargará de crear "/app_output/" DENTRO del contenedor si no existe.

        save_cleaned_data_tsv(cleaned_events_list, OUTPUT_FILE_PATH)

    mongo_client.close()
    print("Proceso de filtrado y homogeneización completado.")

if __name__ == "__main__":
    main()