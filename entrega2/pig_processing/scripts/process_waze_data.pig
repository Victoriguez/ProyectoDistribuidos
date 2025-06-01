--------------------------------------------------------------------------------
-- Script Pig para procesar datos de Waze desde ARCHIVO TSV
-- Archivo: process_waze_data.pig
--------------------------------------------------------------------------------

-- (Sección A) Registrar JARs y Definir UDFs
-- #############################################################################
-- Registrar el script Python que contiene los UDFs.
-- Pig buscará 'waze_udfs.py' en el path /pig_udfs/ DENTRO del contenedor.
-- 'waze_helpers' es el alias que le damos a este conjunto de UDFs.
REGISTER '/pig_udfs/waze_udfs.py' USING jython AS waze_helpers; 
-- NOTA: Usar 'jython' aquí asume que la imagen de Pig (o las librerías que trae Pig 0.17)
-- incluye un intérprete Jython. Si esto falla, el error lo indicará, y
-- tendríamos que cambiar a un UDF de streaming (más complejo de definir para funciones individuales)
-- o usar una imagen de Pig que explícitamente incluya un Jython funcional.


-- (Sección B) Cargar Datos Crudos desde el Archivo TSV
raw_events_from_tsv = LOAD '/pig_input_data/waze_events.tsv' USING PigStorage('\t') 
                   AS (uuid:chararray, 
                       original_waze_type:chararray, 
                       waze_subtype:chararray, 
                       raw_description:chararray, 
                       lon_str:chararray,
                       lat_str:chararray,
                       timestamp_iso_str:chararray);

-- (Sección C) Proyección y Conversión de Tipos Inicial
projected_and_casted = FOREACH raw_events_from_tsv GENERATE
    uuid, original_waze_type, waze_subtype, raw_description,
    (double)lon_str AS lon, (double)lat_str AS lat, timestamp_iso_str;

-- (Sección C.2) Limpieza y Filtrado Básico
filtered_events_basic = FILTER projected_and_casted BY 
    uuid IS NOT NULL AND lon IS NOT NULL AND lat IS NOT NULL AND timestamp_iso_str IS NOT NULL;

-- (Sección D) Estandarización y Transformación
events_with_std_type = FOREACH filtered_events_basic GENERATE
    uuid, original_waze_type, waze_subtype, raw_description, lon, lat, timestamp_iso_str,
    (CASE TRIM(UPPER(original_waze_type)) 
        WHEN 'JAM' THEN 'CONGESTION' WHEN 'ACCIDENT' THEN 'ACCIDENTE'
        WHEN 'HAZARD' THEN 'PELIGRO_VIA' WHEN 'ROAD_CLOSED' THEN 'CORTE_VIAL'
        WHEN 'POLICE' THEN 'CONTROL_POLICIAL' WHEN 'CONSTRUCTION' THEN 'OBRA_VIAL' 
        ELSE ( (TRIM(UPPER(original_waze_type)) == '' OR original_waze_type IS NULL) ? 'DESCONOCIDO' : 'OTRO' )
    END) AS standardized_type;

-- D.2 Usar UDFs para enriquecer los datos con comuna (placeholder) y partes del tiempo
events_enriched = FOREACH events_with_std_type GENERATE
    uuid,
    standardized_type,
    raw_description AS description, -- Usar la descripción ya procesada por el scraper
    lon,
    lat,
    -- Llamada al UDF de comuna (actualmente es un placeholder)
    waze_helpers.determine_comuna_py( (chararray)lon, (chararray)lat ) AS comuna, 
    -- Llamada a los UDFs de timestamp
    waze_helpers.iso_to_hour(timestamp_iso_str) AS hora_del_dia,             
    waze_helpers.iso_to_day_of_week(timestamp_iso_str) AS dia_semana,         
    timestamp_iso_str AS timestamp_original_iso; -- Mantener el timestamp original también

DUMP events_enriched; -- Verificar la salida de los UDFs

data_for_analysis = events_enriched;


-- (Sección E) Análisis Agregados (Ahora usando data_for_analysis que incluye comuna y partes del tiempo)
-- #############################################################################

-- Conteo por Tipo Estandarizado
grouped_by_std_type = GROUP data_for_analysis BY standardized_type;
count_by_std_type = FOREACH grouped_by_std_type {
    GENERATE group AS event_type, COUNT(data_for_analysis) AS total_incidentes;
};
STORE count_by_std_type INTO '/pig_output_data/count_by_standardized_type' USING PigStorage(',');
-- DUMP count_by_std_type;

-- Conteo por Comuna
grouped_by_comuna = GROUP data_for_analysis BY comuna;
count_by_comuna = FOREACH grouped_by_comuna {
    GENERATE group AS comuna_nombre, COUNT(data_for_analysis) AS total_incidentes_comuna;
};
STORE count_by_comuna INTO '/pig_output_data/count_by_comuna' USING PigStorage(',');
-- DUMP count_by_comuna;

-- Conteo por Hora del Día
grouped_by_hour = GROUP data_for_analysis BY hora_del_dia;
count_by_hour = FOREACH grouped_by_hour {
    GENERATE group AS hora, COUNT(data_for_analysis) AS total_incidentes_hora;
};
ordered_by_hour = ORDER count_by_hour BY hora ASC;
STORE ordered_by_hour INTO '/pig_output_data/count_by_hour' USING PigStorage(',');
-- DUMP ordered_by_hour;

-- (Opcional) Guardar la tabla enriquecida completa
-- STORE data_for_analysis INTO '/pig_output_data/all_enriched_events' USING PigStorage('\t');