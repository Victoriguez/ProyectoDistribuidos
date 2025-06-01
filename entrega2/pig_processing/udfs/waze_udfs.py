# Archivo: ProyectoDistribuidos/entrega2/pig_processing/udfs/waze_udfs.py
# coding: utf-8 # Especificar encoding por si acaso

# Importar datetime.datetime explícitamente para evitar conflictos
import datetime as dt_module 
from datetime import timezone

# El decorador @outputSchema es ideal, pero requiere que pig_util.py esté en el classpath de Jython,
# lo cual puede ser complicado de configurar en la imagen Docker sin más pasos.
# Por ahora, omitiremos el decorador y Pig intentará inferir los tipos.
# Si la inferencia falla o es incorrecta, podemos especificar el esquema en el DEFINE del script Pig.

# from pig_util import outputSchema # Comentado por ahora

# @outputSchema("hora:int") # Comentado por ahora
def iso_to_hour(timestamp_iso_str):
    """
    Convierte un string de timestamp ISO 8601 a la hora (entero 0-23).
    Retorna None si el parseo falla.
    """
    if not timestamp_iso_str:
        return None
    try:
        # Python 3.7+ datetime.fromisoformat maneja offsets como +00:00 y Z
        # Asegurarse de que 'Z' se maneje correctamente si aparece.
        datetime_obj = dt_module.datetime.fromisoformat(timestamp_iso_str.replace("Z", "+00:00"))
        return datetime_obj.hour
    except ValueError: # Si fromisoformat falla (ej. formato inesperado)
        # print(f"UDF_iso_to_hour: ValueError parseando '{timestamp_iso_str}'") # Para debug en logs de Pig/Hadoop
        return None
    except Exception as e: # Captura general para otros errores inesperados
        # print(f"UDF_iso_to_hour: Error general parseando '{timestamp_iso_str}': {e}")
        return None

# @outputSchema("dia_semana:int") # Comentado por ahora
def iso_to_day_of_week(timestamp_iso_str):
    """
    Convierte un string de timestamp ISO 8601 al día de la semana (entero, Lunes=0, Domingo=6).
    Retorna None si el parseo falla.
    """
    if not timestamp_iso_str:
        return None
    try:
        datetime_obj = dt_module.datetime.fromisoformat(timestamp_iso_str.replace("Z", "+00:00"))
        return datetime_obj.weekday()
    except ValueError:
        # print(f"UDF_iso_to_day_of_week: ValueError parseando '{timestamp_iso_str}'")
        return None
    except Exception as e:
        # print(f"UDF_iso_to_day_of_week: Error general parseando '{timestamp_iso_str}': {e}")
        return None

# Placeholder para el UDF de comuna - NO LO USAREMOS EN ESTE PASO
# @outputSchema("comuna:chararray") # Comentado por ahora
def determine_comuna_py(lon_str, lat_str):
    # Esta función se implementará después.
    # Por ahora, para evitar errores si se llama accidentalmente:
    if lon_str and lat_str:
        return "COMUNA_PENDIENTE_UDF"
    return None