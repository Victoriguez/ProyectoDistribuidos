# Archivo: ProyectoDistribuidos/entrega2/pig_processing/udfs/waze_udfs.py
# coding: utf-8

import datetime as dt_module 
import json 
import sys 
import os
import io 

COMMUNAS_GEOJSON_DATA = None
GEOJSON_FILE_PATH_IN_PIG_CONTAINER = os.getenv('PIG_GEOJSON_PATH', '/pig_data/comunas_rm.geojson')

def _load_geojson_data_internal():
    global COMMUNAS_GEOJSON_DATA
    # ... (esta función se mantiene igual que la última vez, con los sys.stderr.write)
    if COMMUNAS_GEOJSON_DATA is None:
        sys.stderr.write("UDF_DEBUG: Attempting to load GeoJSON from '{}'...\n".format(GEOJSON_FILE_PATH_IN_PIG_CONTAINER))
        if not os.path.exists(GEOJSON_FILE_PATH_IN_PIG_CONTAINER):
            sys.stderr.write("UDF_DEBUG: ERROR - GeoJSON file NOT FOUND at '{}'\n".format(GEOJSON_FILE_PATH_IN_PIG_CONTAINER))
            COMMUNAS_GEOJSON_DATA = {"type": "FeatureCollection", "features": []} 
            return COMMUNAS_GEOJSON_DATA
        try:
            with io.open(GEOJSON_FILE_PATH_IN_PIG_CONTAINER, 'r', encoding='utf-8') as f:
                COMMUNAS_GEOJSON_DATA = json.load(f)
            if COMMUNAS_GEOJSON_DATA and 'features' in COMMUNAS_GEOJSON_DATA:
                 sys.stderr.write("UDF_DEBUG: GeoJSON loaded. Features: {}\n".format(len(COMMUNAS_GEOJSON_DATA['features'])))
            else:
                sys.stderr.write("UDF_DEBUG: GeoJSON loaded but seems empty or no features key.\n")
                COMMUNAS_GEOJSON_DATA = {"type": "FeatureCollection", "features": []}
        except Exception as e:
            COMMUNAS_GEOJSON_DATA = {"type": "FeatureCollection", "features": []}
            sys.stderr.write("UDF_DEBUG: CRITICAL ERROR loading GeoJSON: {}\n".format(str(e)))
    return COMMUNAS_GEOJSON_DATA


def iso_to_hour(timestamp_iso_str):
    # Simplificar la verificación de entrada para Jython
    if timestamp_iso_str is None or str(timestamp_iso_str).strip() == "": # Convertir a str por si acaso y luego trim
        sys.stderr.write("UDF_DEBUG_HOUR: Received None or empty input: '{}'\n".format(timestamp_iso_str))
        return None
    try:
        # Convertir el input de Jython a un string de Python estándar
        ts_to_parse = str(timestamp_iso_str)
        
        if '+' in ts_to_parse: ts_to_parse = ts_to_parse.split('+')[0]
        elif 'Z' in ts_to_parse: ts_to_parse = ts_to_parse.split('Z')[0]
        if '.' in ts_to_parse: ts_to_parse = ts_to_parse.split('.')[0]
        
        datetime_obj = dt_module.datetime.strptime(ts_to_parse, "%Y-%m-%dT%H:%M:%S")
        return datetime_obj.hour
    except Exception as e: # Capturar cualquier error durante el parseo
        sys.stderr.write("UDF_DEBUG_HOUR: Error parsing '{}': {}\n".format(timestamp_iso_str, str(e)))
        return None

def iso_to_day_of_week(timestamp_iso_str):
    # Simplificar la verificación de entrada para Jython
    if timestamp_iso_str is None or str(timestamp_iso_str).strip() == "": # Convertir a str por si acaso y luego trim
        sys.stderr.write("UDF_DEBUG_DOW: Received None or empty input: '{}'\n".format(timestamp_iso_str))
        return None
    try:
        # Convertir el input de Jython a un string de Python estándar
        ts_to_parse = str(timestamp_iso_str)

        if '+' in ts_to_parse: ts_to_parse = ts_to_parse.split('+')[0]
        elif 'Z' in ts_to_parse: ts_to_parse = ts_to_parse.split('Z')[0]
        if '.' in ts_to_parse: ts_to_parse = ts_to_parse.split('.')[0]
            
        datetime_obj = dt_module.datetime.strptime(ts_to_parse, "%Y-%m-%dT%H:%M:%S")
        return datetime_obj.weekday() 
    except Exception as e:
        sys.stderr.write("UDF_DEBUG_DOW: Error parsing '{}': {}\n".format(timestamp_iso_str, str(e)))
        return None

def determine_comuna_py(lon_str, lat_str):
    _load_geojson_data_internal() # Asegurarse de que se intente cargar
    # Para depurar, simplemente devolvemos un string fijo o los inputs
    if lon_str is not None and lat_str is not None:
        try:
            # Intentar convertir a float para ver si son numéricos
            float(str(lon_str)) 
            float(str(lat_str))
            return u"COMUNA_UDF_CALLED_VALID_INPUTS"
        except:
            return u"COMUNA_UDF_CALLED_INVALID_COORDS"
    return u"COMUNA_UDF_CALLED_NULL_INPUTS"