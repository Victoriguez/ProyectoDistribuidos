--------------------------------------------------------------------------------
-- Script Pig para procesar datos de Waze desde ARCHIVO TSV
-- Archivo: process_waze_data.pig
--------------------------------------------------------------------------------

rmf /pig_output_data/count_by_standardized_type_test; -- Nuevo nombre para esta prueba

REGISTER '/pig_udfs/waze_udfs.py' USING jython AS waze_helpers; 

raw_events_from_tsv = LOAD '/pig_input_data/waze_events.tsv' USING PigStorage('\t') 
                   AS (uuid:chararray, 
                       original_waze_type:chararray, 
                       waze_subtype:chararray, 
                       raw_description:chararray, 
                       lon_str:chararray,
                       lat_str:chararray,
                       timestamp_iso_str:chararray);

projected_and_casted = FOREACH raw_events_from_tsv GENERATE
    uuid, original_waze_type, waze_subtype, raw_description,
    (double)lon_str AS lon, (double)lat_str AS lat, timestamp_iso_str;

filtered_events_basic = FILTER projected_and_casted BY 
    uuid IS NOT NULL AND lon IS NOT NULL AND lat IS NOT NULL AND timestamp_iso_str IS NOT NULL;

events_with_std_type = FOREACH filtered_events_basic GENERATE
    uuid, original_waze_type, waze_subtype, raw_description, lon, lat, timestamp_iso_str,
    (CASE TRIM(UPPER(original_waze_type)) 
        WHEN 'JAM' THEN 'CONGESTION' WHEN 'ACCIDENT' THEN 'ACCIDENTE'
        WHEN 'HAZARD' THEN 'PELIGRO_VIA' WHEN 'ROAD_CLOSED' THEN 'CORTE_VIAL'
        WHEN 'POLICE' THEN 'CONTROL_POLICIAL' WHEN 'CONSTRUCTION' THEN 'OBRA_VIAL' 
        ELSE ( (TRIM(UPPER(original_waze_type)) == '' OR original_waze_type IS NULL) ? 'DESCONOCIDO' : 'OTRO' )
    END) AS standardized_type;
    -- No añadimos count_one aquí todavía

-- Llamar a los UDFs
events_enriched_temp = FOREACH events_with_std_type GENERATE
    uuid,
    standardized_type,
    raw_description AS description,
    lon,
    lat,
    waze_helpers.determine_comuna_py( (chararray)lon, (chararray)lat ) AS comuna, 
    (int)waze_helpers.iso_to_hour(timestamp_iso_str) AS hora_del_dia,             
    (int)waze_helpers.iso_to_day_of_week(timestamp_iso_str) AS dia_semana,         
    timestamp_iso_str AS timestamp_original_iso;

-- Forzar esquema después de UDFs
events_enriched = FOREACH events_enriched_temp GENERATE
    (chararray)uuid AS uuid,
    (chararray)standardized_type AS standardized_type,
    (chararray)description AS description,
    (double)lon AS lon,
    (double)lat AS lat,
    (chararray)comuna AS comuna, 
    (int)hora_del_dia AS hora_del_dia,       
    (int)dia_semana AS dia_semana,   
    (chararray)timestamp_original_iso AS timestamp_original_iso;

DUMP events_enriched; 
    
-- Conteo por Tipo Estandarizado (Usando COUNT directamente sobre la bolsa)
grouped_by_std_type = GROUP events_enriched BY standardized_type;
count_by_std_type = FOREACH grouped_by_std_type {
    GENERATE group AS event_type, COUNT(events_enriched) AS total_incidentes; -- Volver a COUNT(bolsa)
};
STORE count_by_std_type INTO '/pig_output_data/count_by_standardized_type_test' USING PigStorage(',');
DUMP count_by_std_type;

-- Los otros análisis quedan comentados por ahora.
-- grouped_by_comuna = GROUP events_enriched BY comuna;
-- ...
-- grouped_by_hour = GROUP valid_time_data BY hora_del_dia;
-- ...