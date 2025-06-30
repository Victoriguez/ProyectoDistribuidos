# ProyectoDistribuidos/entrega3/es_loader/load_results_to_elasticsearch.py
from elasticsearch import Elasticsearch, helpers
import os, csv, time, sys

# --- Configuración ---
ELASTICSEARCH_HOST = os.getenv('ES_HOST', 'elasticsearch_service')
PIG_OUTPUT_BASE_DIR = '/pig_results'

# --- Archivos a Cargar y sus Índices en Elasticsearch ---
# CORRECCIÓN: Añadir 'redis_prefix' aquí para pasarlo como parámetro
AGGREGATE_FILES_TO_LOAD = {
    'count_by_standardized_type': {
        'filepath': os.path.join(PIG_OUTPUT_BASE_DIR, 'count_by_standardized_type', 'part-r-00000'),
        'index_name': 'stats_incidentes_por_tipo',
        'redis_prefix': 'stats:type:'
    },
    'count_by_comuna': {
        'filepath': os.path.join(PIG_OUTPUT_BASE_DIR, 'count_by_comuna', 'part-r-00000'),
        'index_name': 'stats_incidentes_por_comuna',
        'redis_prefix': 'stats:comuna:'
    },
    'count_by_hour': {
        'filepath': os.path.join(PIG_OUTPUT_BASE_DIR, 'count_by_hour', 'part-r-00000'),
        'index_name': 'stats_incidentes_por_hora',
        'redis_prefix': 'stats:hour:'
    },
    'count_by_day_of_week': {
        'filepath': os.path.join(PIG_OUTPUT_BASE_DIR, 'count_by_day_of_week', 'part-r-00000'),
        'index_name': 'stats_incidentes_por_dia',
        'redis_prefix': 'stats:dow:'
    }
}
ALL_EVENTS_FILE_PATH = os.path.join(PIG_OUTPUT_BASE_DIR, 'all_enriched_events_table', 'part-m-00000')
ALL_EVENTS_INDEX_NAME = 'waze_eventos_procesados'

# --- El resto de las funciones (connect_to_es, create_index_with_mapping, etc.) y main() se mantienen igual ---
# --- que en la última versión que te di. Las incluyo por completitud. ---

def connect_to_es(retry_interval=10, max_retries=12):
    es_host_url = f"http://{ELASTICSEARCH_HOST}:9200"
    print(f"ESLoader: Conectando a Elasticsearch en {es_host_url}...", flush=True)
    for attempt in range(max_retries):
        try:
            es_client = Elasticsearch([es_host_url], request_timeout=30)
            if es_client.ping(): print("ESLoader: Conexión exitosa a Elasticsearch.", flush=True); return es_client
            else: raise ConnectionError("Ping a Elasticsearch falló.")
        except Exception as e:
            print(f"ESLoader: No se pudo conectar (intento {attempt + 1}/{max_retries}): {e}. Reintentando...", flush=True)
            if attempt < max_retries - 1: time.sleep(retry_interval)
            else: return None
    return None

def create_index_with_mapping(es_client, index_name, key_is_numeric=False):
    if es_client.indices.exists(index=index_name): return True
    print(f"ESLoader: Creando índice '{index_name}'...", flush=True)
    properties = {"count": {"type": "long"}}
    if key_is_numeric:
        properties["key"] = {"type": "integer"}
    else:
        properties["key"] = {"type": "keyword"}
    mapping = {"mappings": {"properties": properties}}
    try: es_client.indices.create(index=index_name, body=mapping, ignore=400); return True
    except Exception as e: print(f"ESLoader: ERROR creando índice '{index_name}': {e}", flush=True); return False

def load_aggregate_data(es_client, filepath, index_name, redis_key_prefix): # El parámetro redis_key_prefix ahora se recibirá
    if not os.path.exists(filepath): return 0
    key_is_numeric = redis_key_prefix in ['stats:hour:', 'stats:dow:']
    if not create_index_with_mapping(es_client, index_name, key_is_numeric=key_is_numeric): return 0
    actions = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t');
        for row in reader:
            if len(row) == 2 and row[0] and row[1]:
                key_value = int(row[0]) if key_is_numeric else row[0]
                count_value = int(row[1])
                actions.append({"_index": index_name, "_source": {"key": key_value, "count": count_value}})
    if not actions: print(f"ESLoader: No se encontraron datos válidos en {filepath}", flush=True); return 0
    success, _ = helpers.bulk(es_client, actions)
    print(f"ESLoader: Bulk load para '{index_name}'. Éxito: {success}", flush=True)
    return success

def load_all_events_data(es_client, filepath, index_name):
    full_mapping = {
        "mappings": {"properties": {
            "uuid": {"type": "keyword"}, "standardized_type": {"type": "keyword"},
            "description": {"type": "text"}, "location": {"type": "geo_point"}, 
            "comuna": {"type": "keyword"}, "hora_del_dia": {"type": "integer"},
            "dia_semana": {"type": "integer"}, "timestamp_original_iso": {"type": "date"}
        }}
    }
    if not es_client.indices.exists(index=index_name):
        try: es_client.indices.create(index=index_name, body=full_mapping, ignore=400)
        except Exception as e: print(f"ESLoader: ERROR creando índice principal '{index_name}': {e}", flush=True); return 0

    if not os.path.exists(filepath): print(f"ESLoader: Archivo no encontrado: {filepath}", flush=True); return 0
    actions = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            if len(row) >= 9: # >= 9 para ser más flexible
                try:
                    actions.append({
                        "_index": index_name, "_id": row[0],
                        "_source": {
                            "uuid": row[0], "standardized_type": row[1], "description": row[2],
                            "location": {"lat": float(row[4]), "lon": float(row[3])},
                            "comuna": row[5], "hora_del_dia": int(row[6]) if row[6] else None,
                            "dia_semana": int(row[7]) if row[7] else None,
                            "timestamp_original_iso": row[8] if row[8] else None,
                        }
                    })
                except (ValueError, IndexError): pass
    if not actions: print(f"ESLoader: No se encontraron datos válidos en {filepath}", flush=True); return 0
    success, _ = helpers.bulk(es_client, actions)
    print(f"ESLoader: Bulk load para '{index_name}'. Éxito: {success}", flush=True)
    return success

def main():
    print("ESLoader: Iniciando script...", flush=True)
    es = connect_to_es()
    if not es: sys.exit(1)
    try:
        total_success = 0
        for result_name, info in AGGREGATE_FILES_TO_LOAD.items():
            total_success += load_aggregate_data(es, info['filepath'], info['index_name'], info['redis_prefix']) # Se pasa info['redis_prefix']
        total_success += load_all_events_data(es, ALL_EVENTS_FILE_PATH, ALL_EVENTS_INDEX_NAME)
        if total_success > 0: print("ESLoader: Proceso completado. Se cargaron datos en Elasticsearch.", flush=True); sys.exit(0)
        else: print("ESLoader: Proceso completado, pero NO se cargó ningún registro.", flush=True); sys.exit(1)
    except Exception as e:
        print(f"ESLoader: Un error inesperado ocurrió en main: {e}", flush=True); sys.exit(1)

if __name__ == "__main__":
    main()