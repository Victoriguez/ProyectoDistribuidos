
## Instrucciones de Ejecución del Pipeline Completo (Entrega 2)

Siga estos pasos desde la raíz del repositorio clonado:

1.  **Asegurar Archivo GeoJSON:**
    Verifique que el archivo `comunas_rm.geojson` esté presente en la carpeta `mongo_exporter/`. Este archivo es esencial para que el servicio `mongo_exporter` pueda determinar las comunas.

2.  **Limpiar Ejecuciones Anteriores (Recomendado para una corrida limpia):**
    ```bash
    docker-compose down --remove-orphans
    ```
    Si desea empezar con bases de datos y cachés completamente vacíos (esto eliminará datos persistentes):
    ```bash
    docker volume rm proyectodistribuidos_mongo_data proyectodistribuidos_redis_pig_data
    ```
    *(Los nombres exactos de los volúmenes se pueden verificar con `docker volume ls`).*
    El script `process_waze_data.pig` ya incluye comandos `rmf` para limpiar sus propios directorios de salida antes de cada ejecución.

3.  **Construir Imágenes y Ejecutar el Pipeline:**
    Este comando construirá las imágenes Docker necesarias e iniciará todos los servicios en el orden correcto:
    ```bash
    docker-compose up --build storage scraper mongo_exporter pig_processor redis_actual_cache cache_loader
    ```
    *   La opción `--build` es importante la primera vez o si se han modificado los `Dockerfile`.
    *   Espere a que los servicios `scraper`, `mongo_exporter`, `pig_processor`, y `cache_loader` completen su ejecución (deberían salir con código 0). Los servicios `storage` (MongoDB) y `redis_actual_cache` (Redis) permanecerán activos.

4.  **Observar los Logs (Opcional - para Monitoreo):**
    La terminal donde se ejecuta `docker-compose up` mostrará la salida combinada. Se pueden observar los mensajes de cada servicio para verificar su progreso y finalización.

5.  **Verificación de Resultados:**

    *   **Archivo TSV Intermedio (Salida del `mongo_exporter`):**
        `ProyectoDistribuidos/entrega2/pig_processing/data_input/waze_events.tsv`
        Debería contener los eventos de MongoDB enriquecidos con `comuna`, `hora_del_dia_str`, y `dia_semana_str`.

    *   **Archivos de Salida de Pig:**
        Navegar a `ProyectoDistribuidos/entrega2/pig_processing/data_output/`. Dentro de las subcarpetas (`count_by_standardized_type`, `count_by_comuna`, `count_by_hour`, `count_by_day_of_week`, `all_enriched_events_table`), abrir los archivos `part-r-00000` (o similar) para ver los resultados de los análisis.

    *   **Datos en Redis (Caché):**
        Abrir una nueva terminal y ejecutar:
        ```bash
        docker exec -it redis_cache_for_pig_results redis-cli
        ```
        Dentro de `redis-cli`, probar comandos como:
        ```redis
        KEYS stats:*
        GET stats:type:CONGESTION
        GET stats:comuna:Maipú 
        GET stats:hour:21
        GET stats:dow:4 
        exit
        ```

6.  **Para Detener Todos los Servicios (MongoDB y Redis):**
    En la terminal donde se ejecutó `docker-compose up` (si no se usó `-d`), presionar `Ctrl + C`. O, desde cualquier terminal en la raíz del proyecto:
    ```bash
    docker-compose down
    ```

---

## Descripción Detallada de los Módulos (Entrega 2)

#### 1. Scraper (Servicio: `scraper`)
*   Recolecta datos de alertas de la API GeoRSS de Waze y los almacena en MongoDB (colección `eventos` en BD `waze_db`). Los datos incluyen `uuid_waze`, `type`, `subtype`, `description` (construida), `location` y `timestamp_waze`.

#### 2. Mongo Exporter (Servicio: `mongo_exporter`)
*   Extrae los datos crudos de MongoDB.
*   Utiliza `shapely` y `comunas_rm.geojson` para determinar la comuna de cada evento.
*   Parsea el `timestamp_waze` para extraer la hora del día y el día de la semana.
*   Genera un archivo `waze_events.tsv` delimitado por tabulaciones con los datos enriquecidos, listo para Pig.

#### 3. Pig Processor (Servicio: `pig_processor`)
*   Utiliza Apache Pig 0.17.0 para procesar `waze_events.tsv`.
*   El script `process_waze_data.pig` realiza:
    *   Carga y definición de esquema del TSV.
    *   Filtrado de registros inválidos o incompletos.
    *   Estandarización de tipos de eventos Waze (ej. 'JAM' a 'CONGESTION').
    *   Casteo de campos de hora y día a enteros.
    *   Agregaciones: conteo de incidentes por tipo, por comuna, por hora del día, y por día de la semana.
    *   Almacenamiento de los resultados agregados y de la tabla completa procesada en archivos TSV.

#### 4. Cache Loader (Servicio: `cache_loader`)
*   Lee los archivos TSV de resultados generados por Pig.
*   Se conecta al servicio Redis (`redis_actual_cache`).
*   Almacena los datos agregados (conteos) como pares clave-valor en Redis para un acceso rápido.

#### 5. Servicios de Almacenamiento
*   **MongoDB (Servicio `storage`):** Base de datos para los datos crudos de Waze.
*   **Redis (Servicio `redis_actual_cache`):** Caché para los resultados analíticos de Pig.

---

## Justificación de Decisiones de Diseño Clave

*   **Exportación a TSV antes de Pig:** Dada la naturaleza End-of-Life del conector `mongo-hadoop` y las dificultades para integrar librerías Python con dependencias C (como `shapely`) directamente en UDFs de Pig/Jython, se optó por realizar el enriquecimiento de datos (determinación de comuna y parseo de timestamps) en un script Python (`mongo_exporter`) que genera un archivo TSV.
*   **Procesamiento Principal en Pig:** A pesar del paso de exportación, todo el filtrado subsecuente, la estandarización de tipos de eventos, y los análisis agregados requeridos (incluyendo los que usan los campos de comuna y tiempo) se realizan íntegramente utilizando Apache Pig, cumpliendo con el requisito central de la entrega.
*   **Caché con Redis:** Se seleccionó Redis por su rendimiento y simplicidad para almacenar los resultados agregados, facilitando su consumo en futuras etapas del proyecto (ej. visualización).

---

## Evaluación de Rendimiento (Ejemplo)

*(Esta sección debe ser completada con las mediciones reales obtenidas durante las pruebas).*

Se realizaron pruebas de rendimiento para X eventos, midiendo los tiempos de ejecución de los componentes clave:

| Componente         | Tiempo de Ejecución (X eventos) | Tiempo de Ejecución (Y eventos - opcional) |
| :----------------- | :------------------------------ | :----------------------------------------- |
| `mongo_exporter`   | XX.X s                          | ...                                        |
| `pig_processor`    | YY.Y s                          | ...                                        |
| `cache_loader`     | ZZ.Z s                          | ...                                        |
| **Pipeline Total** | TT.T s                          | ...                                        |

**Observaciones:**
*   *(Análisis breve de los tiempos y cómo escalan).*
*   *(Identificación de la etapa más costosa y posibles cuellos de botella).*
*   *(Limitaciones de la prueba en entorno local vs. clúster distribuido).*

---