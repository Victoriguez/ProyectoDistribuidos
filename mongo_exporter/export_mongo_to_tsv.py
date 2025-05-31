# ProyectoDistribuidos/mongo_exporter/export_mongo_to_tsv.py
import pymongo
import os
import csv # Para escribir TSV correctamente
from datetime import datetime # Para manejar fechas si es necesario al leer

# --- Configuración ---
MONGO_HOST = os.getenv('MONGO_HOST_EXPORTER', 'storage') # Nombre del servicio MongoDB
MONGO_PORT = int(os.getenv('MONGO_PORT_EXPORTER', '27017'))
DB_NAME_EXPORTER = os.getenv('DB_NAME_EXPORTER', 'waze_db')
COLLECTION_NAME_EXPORTER = os.getenv('COLLECTION_NAME_EXPORTER', 'eventos')

# Path de salida DENTRO del contenedor del exporter
# Este path será mapeado a /pig_input_data/ en el host para que Pig lo lea
OUTPUT_TSV_PATH = os.getenv('OUTPUT_TSV_PATH_EXPORTER', '/exported_data/waze_events.tsv')

def connect_to_mongo():
    uri = f"mongodb://{MONGO_HOST}:{MONGO_PORT}/"
    print(f"Exporter: Conectando a MongoDB en {uri}...", flush=True)
    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=10000)
        client.admin.command('ping')
        print("Exporter: Conexión exitosa a MongoDB.", flush=True)
        db = client[DB_NAME_EXPORTER]
        return db[COLLECTION_NAME_EXPORTER]
    except Exception as e:
        print(f"Exporter: Error al conectar a MongoDB: {e}", flush=True)
        exit(1)

def main():
    print("Exporter: Iniciando script de exportación de MongoDB a TSV...", flush=True)
    collection = connect_to_mongo()
    
    # Campos que queremos extraer y el orden en el TSV
    # Basado en tu estructura: uuid_waze, type, subtype, description, location.x, location.y, timestamp_waze
    fields_to_export = [
        'uuid_waze', 'type', 'subtype', 'description', 
        'location_x', 'location_y', 'timestamp_waze'
    ]
    
    # Crear el directorio de salida si no existe (dentro del contenedor)
    output_dir = os.path.dirname(OUTPUT_TSV_PATH)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Exporter: Creado directorio de salida {output_dir}", flush=True)

    print(f"Exporter: Exportando datos a {OUTPUT_TSV_PATH}...", flush=True)
    count = 0
    try:
        with open(OUTPUT_TSV_PATH, 'w', newline='', encoding='utf-8') as tsvfile:
            writer = csv.writer(tsvfile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            
            # Escribir la cabecera (opcional, pero bueno para Pig si la defines en el AS)
            # writer.writerow(fields_to_export) # Pig puede ignorar la cabecera o usarla

            # Iterar sobre los documentos y escribir las filas
            for doc in collection.find({}): # Podrías añadir proyecciones aquí para eficiencia
                count += 1
                row = [
                    doc.get('uuid_waze', ''),
                    doc.get('type', ''),
                    doc.get('subtype', ''),
                    doc.get('description', ''),
                    doc.get('location', {}).get('x', ''), # Extraer x de location
                    doc.get('location', {}).get('y', ''), # Extraer y de location
                    doc.get('timestamp_waze', '')
                ]
                writer.writerow(row)
        print(f"Exporter: Exportación completada. {count} documentos escritos en {OUTPUT_TSV_PATH}.", flush=True)
    except Exception as e:
        print(f"Exporter: Error durante la escritura del archivo TSV: {e}", flush=True)
        exit(1)

if __name__ == "__main__":
    main()