# Archivo: ProyectoDistribuidos/entrega2/pig_processing/udfs/waze_udfs.py
# coding: utf-8

import datetime as dt_module 
import json 
import sys 
import os
import io 
# Intentar importar shapely. Si esto falla aquí, Jython no lo puede encontrar/usar.
try:
    from shapely.geometry import Point, shape
    SHAPELY_AVAILABLE = True
    sys.stderr.write("UDF_DEBUG: Shapely importado exitosamente.\n")
except ImportError:
    SHAPELY_AVAILABLE = False
    sys.stderr.write("UDF_DEBUG: ERROR - No se pudo importar Shapely. La determinación de comuna real no funcionará.\n")

COMMUNAS_GEOJSON_DATA = None
GEOJSON_FILE_PATH_IN_PIG_CONTAINER = os.getenv('PIG_GEOJSON_PATH', '/pig_data/comunas_rm.geojson')

def _load_geojson_data_internal():
    global COMMUNAS_GEOJSON_DATA, COMMUNAS_POLYGONS_SHAPELY # Necesitaremos una nueva lista para polígonos de shapely
    if COMMUNAS_GEOJSON_DATA is None: # Solo cargar una vez
        COMMUNAS_POLYGONS_SHAPELY = [] # Inicializar
        sys.stderr.write("UDF_DEBUG: Intentando cargar GeoJSON desde '{}'...\n".format(GEOJSON_FILE_PATH_IN_PIG_CONTAINER))
        if not os.path.exists(GEOJSON_FILE_PATH_IN_PIG_CONTAINER):
            sys.stderr.write("UDF_DEBUG: ERROR - GeoJSON file NOT FOUND at '{}'\n".format(GEOJSON_FILE_PATH_IN_PIG_CONTAINER))
            COMMUNAS_GEOJSON_DATA = {"type": "FeatureCollection", "features": []} 
            return COMMUNAS_GEOJSON_DATA
        try:
            with io.open(GEOJSON_FILE_PATH_IN_PIG_CONTAINER, 'r', encoding='utf-8') as f:
                COMMUNAS_GEOJSON_DATA = json.load(f) # Guardar el JSON crudo por si acaso
            
            if COMMUNAS_GEOJSON_DATA and 'features' in COMMUNAS_GEOJSON_DATA:
                sys.stderr.write("UDF_DEBUG: GeoJSON cargado. Procesando features para Shapely...\n")
                for feature in COMMUNAS_GEOJSON_DATA['features']:
                    properties = feature.get('properties', {})
                    comuna_name = properties.get('Comuna', properties.get('NOM_COMUNA')) # Ajusta según tu GeoJSON
                    geom = feature.get('geometry')
                    if comuna_name and geom and SHAPELY_AVAILABLE:
                        try:
                            COMMUNAS_POLYGONS_SHAPELY.append((comuna_name, shape(geom)))
                        except Exception as e_shape:
                            sys.stderr.write("UDF_DEBUG: Error creando shape para comuna '{}': {}\n".format(comuna_name, str(e_shape)))
                sys.stderr.write("UDF_DEBUG: Polígonos de Shapely procesados: {}\n".format(len(COMMUNAS_POLYGONS_SHAPELY)))
            else:
                sys.stderr.write("UDF_DEBUG: GeoJSON cargado pero vacío o sin 'features'.\n")
                COMMUNAS_GEOJSON_DATA = {"type": "FeatureCollection", "features": []}
        except Exception as e:
            COMMUNAS_GEOJSON_DATA = {"type": "FeatureCollection", "features": []}
            sys.stderr.write("UDF_DEBUG: CRITICAL ERROR cargando/procesando GeoJSON: {}\n".format(str(e)))
    return COMMUNAS_GEOJSON_DATA # Devolver el JSON crudo, la lógica usará COMMUNAS_POLYGONS_SHAPELY

def iso_to_hour(timestamp_iso_str): # Sin cambios
    if not timestamp_iso_str: return None
    try:
        ts_to_parse = str(timestamp_iso_str);
        if '+' in ts_to_parse: ts_to_parse = ts_to_parse.split('+')[0]
        elif 'Z' in ts_to_parse: ts_to_parse = ts_to_parse.split('Z')[0]
        if '.' in ts_to_parse: ts_to_parse = ts_to_parse.split('.')[0]
        dt_obj = dt_module.datetime.strptime(ts_to_parse, "%Y-%m-%dT%H:%M:%S"); return dt_obj.hour
    except: return None

def iso_to_day_of_week(timestamp_iso_str): # Sin cambios
    if not timestamp_iso_str: return None
    try:
        ts_to_parse = str(timestamp_iso_str);
        if '+' in ts_to_parse: ts_to_parse = ts_to_parse.split('+')[0]
        elif 'Z' in ts_to_parse: ts_to_parse = ts_to_parse.split('Z')[0]
        if '.' in ts_to_parse: ts_to_parse = ts_to_parse.split('.')[0]
        dt_obj = dt_module.datetime.strptime(ts_to_parse, "%Y-%m-%dT%H:%M:%S"); return dt_obj.weekday()
    except: return None

# Cargar el GeoJSON al importar el módulo (solo una vez por proceso de Jython)
COMMUNAS_POLYGONS_SHAPELY = [] # Definir global para que _load_geojson_data_internal la llene
_load_geojson_data_internal() 

def determine_comuna_py(lon_str, lat_str):
    global COMMUNAS_POLYGONS_SHAPELY # Usar la lista global de polígonos de shapely
    
    if not SHAPELY_AVAILABLE:
        return u"SHAPELY_NO_DISPONIBLE"
    
    if not COMMUNAS_POLYGONS_SHAPELY:
         # Intentar cargar de nuevo si está vacío, aunque _load_geojson_data_internal ya lo hace al importar
        _load_geojson_data_internal() 
        if not COMMUNAS_POLYGONS_SHAPELY: # Si sigue vacío después de reintentar
            return u"GEOJSON_NO_CARGADO_EN_UDF"

    if lon_str is None or lat_str is None:
        return u"COORDENADAS_NULAS"
    
    try:
        lon = float(str(lon_str)) # Asegurar conversión
        lat = float(str(lat_str)) # Asegurar conversión
        point = Point(lon, lat)
        for comuna_name, polygon in COMMUNAS_POLYGONS_SHAPELY:
            if polygon.contains(point):
                return unicode(comuna_name) # Devolver como unicode para Jython/Python 2
        return u"FUERA_DE_RM_GEOJSON"
    except ValueError:
        return u"COORDENADAS_NO_NUMERICAS"
    except Exception as e:
        sys.stderr.write("UDF_determine_comuna_py: Error en lógica shapely: {}\n".format(str(e)))
        return u"ERROR_INTERNO_UDF_COMUNA"