--------------------------------------------------------------------------------
-- Script Pig Final para procesar datos de Waze desde ARCHIVO TSV
-- Archivo: process_waze_data.pig
--------------------------------------------------------------------------------

-- Eliminar carpetas de salida anteriores
rmf /pig_output_data/count_by_standardized_type;
rmf /pig_output_data/count_by_comuna;
rmf /pig_output_data/count_by_hour;
rmf /pig_output_data/count_by_day_of_week; -- NUEVO RMF
rmf /pig_output_data/all_enriched_events_table;

raw_events_from_tsv = LOAD '/pig_input_data/waze_events.tsv' USING PigStorage('\t') 
                   AS (uuid:chararray, 
                       original_waze_type:chararray, 
                       waze_subtype:chararray, 
                       raw_description:chararray, 
                       lon_str:chararray,
                       lat_str:chararray,
                       timestamp_original_iso:chararray,
                       comuna:chararray,
                       hora_del_dia_str:chararray,
                       dia_semana_str:chararray);

projected_and_casted = FOREACH raw_events_from_tsv GENERATE
    uuid, original_waze_type, waze_subtype, raw_description,
    (double)lon_str AS lon, (double)lat_str AS lat, timestamp_original_iso,
    TRIM(comuna) AS comuna,
    (TRIM(hora_del_dia_str) == '' ? (int)null : (int)TRIM(hora_del_dia_str)) AS hora_del_dia,
    (TRIM(dia_semana_str) == '' ? (int)null : (int)TRIM(dia_semana_str)) AS dia_semana,
    1L AS count_one;

filtered_events_basic = FILTER projected_and_casted BY 
    uuid IS NOT NULL AND lon IS NOT NULL AND lat IS NOT NULL AND 
    timestamp_original_iso IS NOT NULL AND
    comuna IS NOT NULL AND 
    NOT STARTSWITH(comuna, 'COMUNA_NO_') AND 
    NOT STARTSWITH(comuna, 'FUERA_DE_') AND 
    NOT STARTSWITH(comuna, 'COORDENADAS_INVALIDAS_') AND 
    NOT STARTSWITH(comuna, 'ERROR_EN_');

events_with_std_type = FOREACH filtered_events_basic GENERATE
    uuid, original_waze_type, waze_subtype, raw_description, lon, lat, comuna, hora_del_dia, dia_semana, timestamp_original_iso, count_one,
    (CASE TRIM(UPPER(original_waze_type)) 
        WHEN 'JAM' THEN 'CONGESTION' WHEN 'ACCIDENT' THEN 'ACCIDENTE'
        WHEN 'HAZARD' THEN 'PELIGRO_VIA' WHEN 'ROAD_CLOSED' THEN 'CORTE_VIAL'
        WHEN 'POLICE' THEN 'CONTROL_POLICIAL' WHEN 'CONSTRUCTION' THEN 'OBRA_VIAL' 
        ELSE ( (TRIM(original_waze_type) == '' OR original_waze_type IS NULL) ? 'DESCONOCIDO' : 'OTRO' )
    END) AS standardized_type;
        
data_for_analysis = events_with_std_type;
-- DUMP data_for_analysis; 
    
-- Conteo por Tipo Estandarizado
data_for_type_count = FOREACH data_for_analysis GENERATE standardized_type, count_one;
grouped_by_std_type = GROUP data_for_type_count BY standardized_type;
count_by_std_type = FOREACH grouped_by_std_type {GENERATE group AS event_type, SUM(data_for_type_count.count_one) AS total_incidentes;};
STORE count_by_std_type INTO '/pig_output_data/count_by_standardized_type' USING PigStorage(',');

-- Conteo por Comuna
data_for_comuna_count = FOREACH data_for_analysis GENERATE comuna, count_one;
grouped_by_comuna = GROUP data_for_comuna_count BY comuna;
count_by_comuna = FOREACH grouped_by_comuna {GENERATE group AS comuna_nombre, SUM(data_for_comuna_count.count_one) AS total_incidentes_comuna;};
STORE count_by_comuna INTO '/pig_output_data/count_by_comuna' USING PigStorage(',');

-- Conteo por Hora del Día
valid_time_data_hour = FILTER data_for_analysis BY hora_del_dia IS NOT NULL; -- Renombrado para evitar colisión
data_for_hour_count = FOREACH valid_time_data_hour GENERATE hora_del_dia, count_one;
grouped_by_hour = GROUP data_for_hour_count BY hora_del_dia;
count_by_hour = FOREACH grouped_by_hour {GENERATE group AS hora, SUM(data_for_hour_count.count_one) AS total_incidentes_hora;};
ordered_by_hour = ORDER count_by_hour BY hora ASC;
STORE ordered_by_hour INTO '/pig_output_data/count_by_hour' USING PigStorage(',');

-- Conteo por Día de la Semana (Lunes=0, Domingo=6)
valid_time_data_dow = FILTER data_for_analysis BY dia_semana IS NOT NULL; -- Renombrado
data_for_dow_count = FOREACH valid_time_data_dow GENERATE dia_semana, count_one;
grouped_by_dow = GROUP data_for_dow_count BY dia_semana;
count_by_dow = FOREACH grouped_by_dow {GENERATE group AS dia, SUM(data_for_dow_count.count_one) AS total_incidentes_dia;};
ordered_by_dow = ORDER count_by_dow BY dia ASC;
STORE ordered_by_dow INTO '/pig_output_data/count_by_day_of_week' USING PigStorage(',');
DUMP ordered_by_dow; -- Para ver este resultado

STORE data_for_analysis INTO '/pig_output_data/all_enriched_events_table' USING PigStorage('\t');