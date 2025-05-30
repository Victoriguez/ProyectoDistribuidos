-- Archivo: test_load_store.pig

-- Cargar datos desde el archivo TSV
raw_data = LOAD '/pig_input_data/test_events.tsv' USING PigStorage('\t') 
           AS (event_id:chararray, 
               type:chararray, 
               lon:double, 
               lat:double, 
               timestamp_str:chararray, 
               description:chararray);

-- Simplemente mostrar los datos cargados (para verificar)
DUMP raw_data;

-- Contar eventos por tipo (un procesamiento simple)
grouped_by_type = GROUP raw_data BY type;
count_by_type = FOREACH grouped_by_type GENERATE group AS event_type, COUNT(raw_data) AS total;

-- Mostrar el conteo
DUMP count_by_type;

-- Guardar el resultado en un archivo TSV
STORE count_by_type INTO '/pig_output_data/count_by_type_result' USING PigStorage('\t'); 

-- PRINT 'Script Pig de prueba completado.'; -- Comentada o eliminada