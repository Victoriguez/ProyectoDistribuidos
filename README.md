## Instrucciones de Ejecución del Pipeline Completo (Entrega 2)

Siga estos pasos desde la raíz del repositorio clonado (`ProyectoDistribuidos/`):

1.  **Asegurar Archivo GeoJSON:**
    Verifique que el archivo `comunas_rm.geojson` esté presente en la carpeta `mongo_exporter/`.

2.  **Limpiar Ejecuciones Anteriores (Recomendado):**
    ```bash
    docker-compose down --remove-orphans
    ```
    Opcionalmente, para limpiar datos persistentes de MongoDB y Redis:
    ```bash
    docker volume rm proyectodistribuidos_mongo_data proyectodistribuidos_redis_pig_data
    ```
    *(Verifique los nombres exactos de los volúmenes con `docker volume ls` si es necesario).*
    El script Pig (`process_waze_data.pig`) ya incluye comandos `rmf` para limpiar sus propios directorios de salida.

3.  **Construir Imágenes Docker (si es la primera vez o hay cambios en Dockerfiles):**
    ```bash
    docker-compose build
    ```

4.  **Ejecutar el Pipeline Completo:**
    Este comando iniciará todos los servicios. Los servicios de "job" (`scraper`, `mongo_exporter`, `pig_processor`, `cache_loader`) se ejecutarán secuencialmente. Los servicios de base de datos (`storage`, `redis_actual_cache`) permanecerán corriendo.
    ```bash
    docker-compose up storage redis_actual_cache scraper mongo_exporter pig_processor cache_loader
    ```
    *   Observe los logs en la terminal para monitorear el progreso.
    *   `scraper`, `mongo_exporter`, `pig_processor`, y `cache_loader` deberían salir con código 0.
    *   La terminal se quedará mostrando los logs de `storage` y `redis_actual_cache`.

5.  **Verificación de Resultados:**

    *   **Archivo TSV Intermedio (Salida del `mongo_exporter`):**
        `ProyectoDistribuidos/entrega2/pig_processing/data_input/waze_events.tsv`

    *   **Archivos de Salida de Pig:**
        Navegar a `ProyectoDistribuidos/entrega2/pig_processing/data_output/`. Revisar los archivos `part-r-00000` en las subcarpetas:
        *   `count_by_standardized_type/`
        *   `count_by_comuna/`
        *   `count_by_hour/`
        *   `count_by_day_of_week/`
        *   `all_enriched_events_table/`

    *   **Datos en Redis:**
        Abrir una **NUEVA terminal**, navegar a la raíz del proyecto y ejecutar:
        ```bash
        docker exec -it redis_cache_for_pig_results redis-cli
        ```
        Dentro de `redis-cli`, probar:
        ```redis
        KEYS stats:*
        GET stats:type:CONGESTION
        GET stats:comuna:Maipú
        exit
        ```

6.  **Para Detener Todos los Servicios (MongoDB y Redis):**
    En la terminal donde ejecutó `docker-compose up`, presionar `Ctrl + C`.
    O, desde cualquier terminal en la raíz del proyecto:
    ```bash
    docker-compose down
    ```
---

## Descripción Detallada de los Módulos (Entrega 2)

#### 1. Scraper (Servicio: `scraper`)
*   Recolecta datos de alertas de la API GeoRSS de Waze y los almacena en MongoDB (colección `eventos` en BD `waze_db`).

#### 2. Mongo Exporter (Servicio: `mongo_exporter`)
*   Extrae datos de MongoDB.
*   Utiliza `shapely` y `comunas_rm.geojson` para determinar la comuna.
*   Parsea el timestamp para extraer hora del día y día de la semana.
*   Genera `waze_events.tsv` con datos enriquecidos.

#### 3. Pig Processor (Servicio: `pig_processor`)
*   Utiliza Apache Pig 0.17.0 para procesar `waze_events.tsv`.
*   El script `process_waze_data.pig` realiza filtrado, estandarización de tipos, y análisis agregados (conteo por tipo, comuna, hora, día).
*   Guarda resultados agregados y la tabla completa procesada en archivos TSV.

#### 4. Cache Loader (Servicio: `cache_loader`)
*   Lee los archivos TSV de resultados generados por Pig.
*   Se conecta al servicio Redis (`redis_actual_cache`).
*   Almacena los datos agregados en Redis.

#### 5. Servicios de Almacenamiento
*   **MongoDB (Servicio `storage`):** Base de datos para los datos crudos de Waze.
*   **Redis (Servicio `redis_actual_cache`):** Caché para los resultados analíticos de Pig.

---

## Justificación de Decisiones de Diseño Clave

*   **Exportación a TSV antes de Pig:** Dada la naturaleza End-of-Life del conector `mongo-hadoop` y las dificultades para integrar librerías Python con dependencias C (como `shapely`) directamente en UDFs de Pig/Jython, se optó por realizar el enriquecimiento de datos (determinación de comuna y parseo de timestamps) en el script Python `export_mongo_to_tsv.py`.
*   **Procesamiento Principal en Pig:** Una vez que los datos son ingeridos por Pig desde el archivo TSV, todo el filtrado, estandarización y análisis agregados se realizan íntegramente utilizando Apache Pig.
*   **Caché con Redis:** Se utiliza Redis por su rendimiento para almacenar los resultados agregados, facilitando su consumo futuro.

---

## Evaluación de Rendimiento (Ejemplo)

*(Esta sección debe ser completada por el alumno con las mediciones reales obtenidas durante las pruebas).*

Se realizaron pruebas de rendimiento para X eventos, midiendo los tiempos de ejecución de los componentes clave:

| Componente         | Tiempo de Ejecución (X eventos) |
| :----------------- | :------------------------------ |
| `mongo_exporter`   | *(ej. XX.X s)*                  |
| `pig_processor`    | *(ej. YY.Y s)*                  |
| `cache_loader`     | *(ej. ZZ.Z s)*                  |
| **Pipeline Total** | *(ej. TT.T s)*                  |

**Observaciones:**
*   *(Análisis breve de los tiempos).*
*   *(Identificación de la etapa más costosa).*
*   *(Limitaciones de la prueba en entorno local).*

---