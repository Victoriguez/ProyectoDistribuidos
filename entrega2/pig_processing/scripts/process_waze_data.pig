--------------------------------------------------------------------------------
-- Script Pig para procesar datos de Waze desde ARCHIVO TSV
-- Archivo: process_waze_data.pig
--------------------------------------------------------------------------------

raw_events_from_tsv = LOAD '/pig_input_data/waze_events.tsv' USING PigStorage('\t') 
                   AS (uuid:chararray, 
                       original_waze_type:chararray, 
                       waze_subtype:chararray, 
                       raw_description:chararray, 
                       lon_str:chararray,
                       lat_str:chararray,
                       timestamp_iso_str:chararray);

projected_and_casted = FOREACH raw_events_from_tsv GENERATE
    uuid,
    original_waze_type,
    waze_subtype,
    raw_description,
    (double)lon_str AS lon, 
    (double)lat_str AS lat, 
    timestamp_iso_str;

filtered_events_basic = FILTER projected_and_casted BY 
    uuid IS NOT NULL AND 
    lon IS NOT NULL AND 
    lat IS NOT NULL AND 
    timestamp_iso_str IS NOT NULL;

events_with_std_type = FOREACH filtered_events_basic GENERATE
    uuid,
    original_waze_type,
    waze_subtype,
    raw_description,
    lon,
    lat,
    timestamp_iso_str,
    (CASE TRIM(UPPER(original_waze_type)) 
        WHEN 'JAM' THEN 'CONGESTION'
        WHEN 'ACCIDENT' THEN 'ACCIDENTE'
        WHEN 'HAZARD' THEN 'PELIGRO_VIA'
        WHEN 'ROAD_CLOSED' THEN 'CORTE_VIAL'
        WHEN 'POLICE' THEN 'CONTROL_POLICIAL'
        WHEN 'CONSTRUCTION' THEN 'OBRA_VIAL' 
        ELSE ( (TRIM(UPPER(original_waze_type)) == '' OR original_waze_type IS NULL) ? 'DESCONOCIDO' : 'OTRO' )
    END) AS standardized_type;

-- DUMP events_with_std_type; -- Comentado para no inundar la salida

grouped_by_std_type = GROUP events_with_std_type BY standardized_type;

-- INTENTO CON SINTAXIS DE BLOQUE PARA FOREACH GENERATE
count_by_std_type = FOREACH grouped_by_std_type {
    -- 'events_with_std_type' aquí es la bolsa de tuplas para el 'group' actual
    GENERATE group AS event_type, 
             COUNT(events_with_std_type) AS total_incidentes;
};

STORE count_by_std_type INTO '/pig_output_data/count_by_standardized_type_output' USING PigStorage(',');
DUMP count_by_std_type;