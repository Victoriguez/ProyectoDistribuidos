--------------------------------------------------------------------------------
-- Script Pig Final para procesar datos de Waze
--------------------------------------------------------------------------------

rmf /pig_output_data/count_by_standardized_type;
rmf /pig_output_data/count_by_comuna;
rmf /pig_output_data/count_by_hour;
rmf /pig_output_data/count_by_day_of_week;
rmf /pig_output_data/all_enriched_events_table;

raw_events = LOAD '/pig_input_data/waze_events.tsv' USING PigStorage('\t') 
             AS (uuid:chararray, standardized_type:chararray, description:chararray,
                 lon_str:chararray, lat_str:chararray, comuna:chararray,
                 hora_del_dia_str:chararray, dia_semana_str:chararray, timestamp_original_iso:chararray);

projected_and_casted = FOREACH raw_events GENERATE
    uuid, standardized_type, description,
    (double)lon_str AS lon, (double)lat_str AS lat,
    TRIM(comuna) AS comuna,
    (TRIM(hora_del_dia_str) == '' ? (int)null : (int)TRIM(hora_del_dia_str)) AS hora_del_dia,
    (TRIM(dia_semana_str) == '' ? (int)null : (int)TRIM(dia_semana_str)) AS dia_semana,
    timestamp_original_iso,
    1L AS count_one;

filtered_data = FILTER projected_and_casted BY uuid IS NOT NULL AND lon IS NOT NULL AND comuna IS NOT NULL AND NOT STARTSWITH(comuna, 'FUERA_DE_');

-- Conteo por Tipo Estandarizado
data_for_type_count = FOREACH filtered_data GENERATE standardized_type, count_one;
grouped_by_std_type = GROUP data_for_type_count BY standardized_type;
count_by_std_type = FOREACH grouped_by_std_type {GENERATE group, SUM(data_for_type_count.count_one);};
STORE count_by_std_type INTO '/pig_output_data/count_by_standardized_type' USING PigStorage('\t');

-- Conteo por Comuna
data_for_comuna_count = FOREACH filtered_data GENERATE comuna, count_one;
grouped_by_comuna = GROUP data_for_comuna_count BY comuna;
count_by_comuna = FOREACH grouped_by_comuna {GENERATE group, SUM(data_for_comuna_count.count_one);};
STORE count_by_comuna INTO '/pig_output_data/count_by_comuna' USING PigStorage('\t');

-- Conteo por Hora del Día
valid_time_data_hour = FILTER filtered_data BY hora_del_dia IS NOT NULL;
data_for_hour_count = FOREACH valid_time_data_hour GENERATE hora_del_dia, count_one;
grouped_by_hour = GROUP data_for_hour_count BY hora_del_dia;
count_by_hour = FOREACH grouped_by_hour {GENERATE group, SUM(data_for_hour_count.count_one);};
ordered_by_hour = ORDER count_by_hour BY $0 ASC;
STORE ordered_by_hour INTO '/pig_output_data/count_by_hour' USING PigStorage('\t');

-- Conteo por Día de la Semana
valid_time_data_dow = FILTER filtered_data BY dia_semana IS NOT NULL;
data_for_dow_count = FOREACH valid_time_data_dow GENERATE dia_semana, count_one;
grouped_by_dow = GROUP data_for_dow_count BY dia_semana;
count_by_dow = FOREACH grouped_by_dow {GENERATE group, SUM(data_for_dow_count.count_one);};
ordered_by_dow = ORDER count_by_dow BY $0 ASC;
STORE ordered_by_dow INTO '/pig_output_data/count_by_day_of_week' USING PigStorage('\t');

-- Guardar la tabla enriquecida completa (con las 10 columnas)
STORE filtered_data INTO '/pig_output_data/all_enriched_events_table' USING PigStorage('\t');