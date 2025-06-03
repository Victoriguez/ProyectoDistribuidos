# ProyectoDistribuidos/cache_loader/load_results_to_redis.py
import redis
import os
import csv
import time

REDIS_HOST = os.getenv('REDIS_HOST_LOADER', 'cache')
REDIS_PORT = int(os.getenv('REDIS_PORT_LOADER', 6379))
PIG_OUTPUT_BASE_DIR = '/pig_results_input'
RESULTS_FILES_INFO = {
    'count_by_standardized_type': {
        'filepath': os.path.join(PIG_OUTPUT_BASE_DIR, 'count_by_standardized_type', 'part-r-00000'),
        'redis_prefix': 'stats:type:'
    },
    'count_by_comuna': {
        'filepath': os.path.join(PIG_OUTPUT_BASE_DIR, 'count_by_comuna', 'part-r-00000'),
        'redis_prefix': 'stats:comuna:'
    },
    'count_by_hour': {
        'filepath': os.path.join(PIG_OUTPUT_BASE_DIR, 'count_by_hour', 'part-r-00000'),
        'redis_prefix': 'stats:hour:'
    },
    'count_by_day_of_week': {
        'filepath': os.path.join(PIG_OUTPUT_BASE_DIR, 'count_by_day_of_week', 'part-r-00000'),
        'redis_prefix': 'stats:dow:'
    }
}

def connect_to_redis(retry_interval=5, max_retries=12):
    print(f"CacheLoader: Conectando a Redis en {REDIS_HOST}:{REDIS_PORT}...", flush=True)
    for attempt in range(max_retries):
        try:
            r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
            r.ping()
            print("CacheLoader: Conexión exitosa a Redis.", flush=True)
            return r
        except redis.exceptions.ConnectionError as e:
            print(f"CacheLoader: No se pudo conectar (intento {attempt + 1}/{max_retries}): {e}. Reintentando...", flush=True)
            if attempt < max_retries - 1: time.sleep(retry_interval)
            else: print("CacheLoader: Máximos reintentos alcanzados. Saliendo.", flush=True); exit(1)
    return None

def load_tsv_to_redis(redis_client, filepath, redis_key_prefix):
    if not os.path.exists(filepath):
        print(f"CacheLoader: ARCHIVO NO ENCONTRADO, omitiendo: {filepath}", flush=True)
        return 0
    
    print(f"CacheLoader: Procesando archivo {filepath} para Redis con prefijo '{redis_key_prefix}'...", flush=True)
    count_loaded = 0
    rows_inspected = 0
    try:
        with open(filepath, 'r', encoding='utf-8') as tsvfile:
            # LEER LÍNEA POR LÍNEA MANUALMENTE PARA DEBUG
            for i, line_content in enumerate(tsvfile):
                rows_inspected += 1
                # Imprimir la línea cruda y su representación para ver caracteres ocultos
                print(f"CacheLoader: RAW Line {i+1}: '{line_content.strip()}' (repr: {repr(line_content.strip())})", flush=True) 
                
                # Usar csv.reader en una sola línea para parsearla
                # Esto es un poco ineficiente pero bueno para debug
                # Creamos un "falso" iterable de una sola línea para csv.reader
                line_iterable = [line_content.strip()] # Asegurarse que no haya líneas vacías al final
                if not line_content.strip():
                    print(f"CacheLoader: Línea {i+1} está vacía (después de strip), omitiendo.", flush=True)
                    continue

                reader = csv.reader(line_iterable, delimiter='\t')
                for row in reader: # Debería iterar solo una vez
                    print(f"CacheLoader: Parsed Row {i+1}: {row} (longitud: {len(row)})", flush=True)
                    
                    if not row: 
                        print(f"CacheLoader: Fila {i+1} (después de csv.reader) está vacía, omitiendo.", flush=True)
                        continue

                    if len(row) == 2:
                        key_suffix = str(row[0]).strip()
                        value = str(row[1]).strip()
                        
                        if not key_suffix or key_suffix.lower() == 'null': 
                            print(f"CacheLoader: Clave vacía o 'null' en fila {i+1}, omitiendo: {row}", flush=True)
                            continue
                        if not value or value.lower() == 'null':
                            value = "0" 

                        redis_key = f"{redis_key_prefix}{key_suffix}"
                        redis_client.set(redis_key, value)
                        print(f"CacheLoader: SET {redis_key} = {value}", flush=True)
                        count_loaded += 1
                    else:
                        print(f"CacheLoader: Fila {i+1} con formato incorrecto omitida (esperaba 2 columnas, obtuvo {len(row)}): {row}", flush=True)
        
        print(f"CacheLoader: {rows_inspected} filas inspeccionadas en {filepath}.", flush=True)
        print(f"CacheLoader: {count_loaded} registros cargados desde {filepath}", flush=True)
        return count_loaded
    except Exception as e:
        print(f"CacheLoader: Error procesando archivo {filepath}: {e}", flush=True)
        return 0

def main():
    print("CacheLoader: Iniciando script para cargar resultados de Pig en Redis...", flush=True)
    redis_conn = connect_to_redis()
    if not redis_conn: return

    total_records_loaded = 0
    active_results_files = {} # Solo procesar los que existen

    for result_name, info in RESULTS_FILES_INFO.items():
        if os.path.exists(info['filepath']):
            active_results_files[result_name] = info
        else:
            print(f"CacheLoader: Archivo para '{result_name}' NO encontrado en {info['filepath']}, se omitirá.", flush=True)
            
    for result_name, info in active_results_files.items():
        print(f"\nCacheLoader: Cargando resultados para '{result_name}'...", flush=True)
        num = load_tsv_to_redis(redis_conn, info['filepath'], info['redis_prefix'])
        total_records_loaded += num
    
    print(f"\nCacheLoader: Proceso completado. Total de registros agregados cargados en Redis: {total_records_loaded}", flush=True)

if __name__ == "__main__":
    main()