# Proyecto de Sistemas Distribuidos - Entrega 2: Procesamiento y Análisis de Tráfico

## Descripción General

Esta segunda entrega del proyecto se enfoca en el procesamiento y análisis de los datos de tráfico recolectados en la Entrega 1. El objetivo es transformar los datos crudos de Waze, almacenados en MongoDB, en información agregada y útil. Para ello, se implementa un pipeline que enriquece los datos, los procesa con Apache Pig, y finalmente carga los resultados analíticos en un caché Redis para su futura visualización.

El pipeline de la Entrega 2 se compone de los siguientes módulos principales, orquestados por Docker Compose:

1.  **Scraper (Mejorado)**: Continúa recolectando datos de Waze.
2.  **Almacenamiento (MongoDB)**: Persiste los datos de Waze.
3.  **Mongo Exporter (Python)**: Extrae datos de MongoDB, los enriquece (comuna, hora, día) y los guarda como un archivo TSV.
4.  **Pig Processor (Apache Pig)**: Procesa el archivo TSV para realizar análisis agregados.
5.  **Cache Loader (Python)**: Carga los resultados de Pig en Redis.
6.  **Sistema de Caché (Redis)**: Almacena los resultados analíticos.

---

## 1. Scraper (Mejorado)

El scraper, basado en el de la Entrega 1, se conecta a la API GeoRSS de Waze Live Map para extraer información de alertas en la Región Metropolitana de Santiago, Chile.

-   **Mejoras:** Ahora está configurado para extraer campos más detallados como `type`, `subtype`, `description` (construida), `uuid_waze` (identificador único), `location`, y `timestamp_waze`.
-   Sigue guardando los eventos en MongoDB (`waze_db.eventos`).
-   El número de eventos a recolectar es configurable mediante la variable de entorno `MAX_EVENTS_TO_COLLECT`.

### Endpoint consultado

https://www.waze.com/live-map/api/georss?top={TOP}&bottom={BOTTOM}&left={LEFT}&right={RIGHT}&env=row&types=alerts

*(Las coordenadas y tipos pueden ser configurados a través de variables de entorno en el scraper).*

---

## 2. Almacenamiento (MongoDB - Servicio `storage`)

Se reutiliza MongoDB (versión 6.0) de la Entrega 1 por su eficiencia en la ingesta de datos semi-estructurados.

-   Se aloja en un contenedor Docker llamado `mongo-storage`.
-   Base de datos: `waze_db`
-   Colección: `eventos`
-   Los datos son persistidos usando un volumen Docker (`mongo_data`).

---

## 3. Mongo Exporter (Servicio `mongo_exporter`)

Este nuevo módulo en Python es responsable de la extracción, pre-procesamiento y enriquecimiento de los datos antes de la ingesta por Apache Pig.

-   **Tecnología:** Python, con librerías `pymongo`, `shapely`, `json`, `csv`.
-   **Funcionalidad:**
    -   Lee los datos de la colección `eventos` de MongoDB.
    -   Carga un archivo `comunas_rm.geojson` (incluido en la carpeta `mongo_exporter/`).
    -   Utiliza `shapely` para determinar la **comuna** de cada evento a partir de sus coordenadas.
    -   Parsea el `timestamp_waze` para extraer la **hora del día** y el **día de la semana**.
    -   Escribe los datos enriquecidos (uuid, tipo, subtipo, descripción, lon, lat, timestamp, comuna, hora, día) en un archivo `waze_events.tsv` delimitado por tabulaciones.
-   **Salida:** El archivo `waze_events.tsv` se guarda en un volumen compartido (`./entrega2/pig_processing/data_input/`) para ser consumido por el `Pig Processor`.
-   **Justificación:** Se optó por realizar estas transformaciones (especialmente la determinación de comunas con `shapely`) en Python debido a las complejidades y limitaciones de integrar librerías con dependencias C (como GEOS, requerida por `shapely`) directamente en el entorno de ejecución de Pig UDFs basado en Jython.

---

## 4. Pig Processor (Servicio `pig_processor`)

Este módulo es el núcleo del análisis de datos, utilizando Apache Pig 0.17.0.

-   **Tecnología:** Apache Pig ejecutándose en modo local (`-x local`) dentro de un contenedor Docker personalizado (basado en OpenJDK 11).
-   **Entrada:** Lee el archivo `waze_events.tsv` (generado por `mongo_exporter`).
-   **Script Principal:** `process_waze_data.pig`
-   **Funcionalidades:**
    -   **Carga y Definición de Esquema:** Carga el TSV y define los tipos de datos.
    -   **Filtrado:** Elimina registros con campos esenciales nulos o comunas inválidas.
    *   **Estandarización de Tipos:** Mapea los tipos de eventos crudos de Waze a categorías estándar (CONGESTION, ACCIDENTE, etc.) usando lógica `CASE`.
    *   **Agregaciones:** Realiza los siguientes análisis:
        *   Conteo de incidentes por tipo estandarizado.
        *   Conteo de incidentes por comuna.
        *   Conteo de incidentes por hora del día.
        *   Conteo de incidentes por día de la semana.
    *   **Salida:** Guarda cada resultado agregado en archivos TSV separados dentro de la carpeta `/pig_output_data/` (mapeada al volumen local `./entrega2/pig_processing/data_output/`). También guarda una tabla con todos los eventos enriquecidos.

---

## 5. Cache Loader (Servicio `cache_loader`)

Este nuevo módulo en Python se encarga de cargar los resultados analíticos generados por Pig en el caché Redis.

-   **Tecnología:** Python, con librería `redis`.
-   **Funcionalidad:**
    -   Se ejecuta después de que `pig_processor` completa su tarea.
    -   Lee los archivos TSV de resultados de Pig (conteo por tipo, comuna, hora, día).
    -   Se conecta al servicio Redis.
    -   Almacena los datos agregados como pares clave-valor en Redis, utilizando prefijos para organización (ej. `stats:type:CONGESTION`, `stats:comuna:Lampa`).

---

## 6. Sistema de Caché (Servicio `cache` - Redis)

Se reutiliza y configura el servicio Redis para actuar como un caché de los resultados procesados.

-   **Tecnología:** Redis (imagen oficial de Docker, ej. `redis:latest`).
-   **Funcionalidad:** Almacena los conteos y agregaciones finales para un acceso rápido, pensando en la Entrega 3 (Visualización).
-   **Persistencia:** Se puede configurar con un volumen Docker (`redis_data`) para persistencia.

---

## Uso con Docker (Entrega 2)

### 1. Asegurar Archivos Necesarios

-   Verifica que `mongo_exporter/comunas_rm.geojson` exista.

### 2. Limpiar Ejecuciones Anteriores (Opcional)

```bash
docker-compose down --remove-orphans
```

Si deseas limpiar los resultados anteriores de Pig para una nueva ejecución:

  ### En PowerShell (Windows)

    Remove-Item -Recurse -Force ./entrega2/pig_processing/data_output/*

  ### En Bash (Linux/macOS)

    rm -rf ./entrega2/pig_processing/data_output/*

### 3. Construir y Ejecutar el Pipeline Completo

Este comando orquestará todos los servicios en el orden correcto:

- docker-compose up --build storage scraper mongo_exporter pig_processor cache_loader cache

La opción --build es importante la primera vez o si se han modificado los Dockerfiles.

### 4. Verificar Resultados

MongoDB:
  ```bash
  docker exec -it mongo-storage mongosh
  ```
- Dentro de mongosh: use waze_db; db.eventos.countDocuments();

Archivo TSV Intermedio:
`ProyectoDistribuidos/entrega2/pig_processing/data_input/waze_events.tsv`

Archivos de Salida de Pig:
Dentro de ProyectoDistribuidos/entrega2/pig_processing/data_output/, revisa las subcarpetas:

  - `count_by_standardized_type/part-r-00000`

  - `count_by_comuna/part-r-00000`

  - `count_by_hour/part-r-00000`

  - `count_by_day_of_week/part-r-00000`

  - `all_enriched_events_table/part-r-00000`

Datos en Redis:
   ```bash
  docker exec -it redis_cache_service redis-cli
  ```

  Dentro de redis-cli, prueba: `GET stats:type:CONGESTION, GET stats:comuna:Lampa, KEYS stats:*`

  ### 5. Detener los Servicios

  ```bash
  docker-compose down
  ```

  ### Repositorio

   https://github.com/Victoriguez/ProyectoDistribuidos



## Instrucciones de Ejecución del Pipeline Completo

1.  **Clonar el Repositorio (si es necesario):**
    ```bash
    git clone [URL_DE_TU_REPOSITORIO_GIT]
    cd ProyectoDistribuidos
    ```

2.  **Asegurar la Ubicación del Archivo GeoJSON:**
    El archivo `comunas_rm.geojson` debe estar presente en la carpeta `mongo_exporter/` para que el servicio `mongo_exporter` pueda determinar las comunas.

3.  **Limpiar Ejecuciones Anteriores (Recomendado para una corrida limpia):**
    Desde la raíz del proyecto (`ProyectoDistribuidos/`) en tu terminal (PowerShell/bash):
    ```bash
    docker-compose down --remove-orphans
    ```
    Elimina manualmente las carpetas de salida de Pig si el script Pig no tiene `rmf` o si quieres asegurar una pizarra limpia:
    ```powershell
    # En PowerShell
    Remove-Item -Recurse -Force ./entrega2/pig_processing/data_output/*
    ```
    ```bash
    # En bash (Linux/macOS)
    # rm -rf ./entrega2/pig_processing/data_output/*
    ```
    *(Nota: El script Pig `process_waze_data.pig` proporcionado ya incluye comandos `rmf` para limpiar sus directorios de salida).*

4.  **Ejecutar el Pipeline Completo:**
    Este comando construirá las imágenes necesarias (la primera vez o si los Dockerfiles cambiaron) e iniciará todos los servicios en el orden correcto definido por `depends_on`.
    ```bash
    docker-compose up --build storage scraper mongo_exporter pig_processor cache_loader cache
    ```
    *   `--build`: Asegura que las imágenes se construyan si hay cambios en los Dockerfiles.
    *   Se incluyen todos los servicios relevantes para la Entrega 2.
    *   Espera a que todos los servicios terminen su ejecución (scraper, mongo_exporter, pig_processor, cache_loader saldrán con código 0). Los servicios `storage` (MongoDB) y `cache` (Redis) permanecerán corriendo.

5.  **Observar los Logs:**
    La terminal mostrará los logs de todos los servicios. Presta atención a:
    *   **Scraper:** Mensajes de recolección de eventos.
    *   **Mongo Exporter:** Mensajes de conexión a MongoDB, carga de GeoJSON, procesamiento de comunas/timestamps y escritura del archivo TSV (ej. "Exportación completada. X documentos escritos.").
    *   **Pig Processor:** Mensajes de inicio de Pig, lectura del TSV (ej. "Successfully read X records..."), y la salida de los `DUMP` que tengas activos. Debería terminar con "Pig script completed...".
    *   **Cache Loader:** Mensajes de conexión a Redis, lectura de los archivos de resultados de Pig y carga de datos en Redis (ej. "SET stats:type:CONGESTION = YYY").

6.  **Para Detener los Servicios que Quedan Corriendo (MongoDB, Redis):**
    Presiona `Ctrl + C` en la terminal donde ejecutaste `docker-compose up`. Si no se detienen, abre otra terminal y ejecuta:
    ```bash
    docker-compose down
    ```

---

## Descripción de los Componentes del Pipeline

#### 1. Scraper (Recolector de Datos de Waze)
*   **Ubicación:** `scraper/`
*   **Tecnología:** Python, `requests`.
*   **Función:** Consulta la API `georss` de Waze para obtener datos de alertas (tipo, subtipo, descripción, ubicación, timestamp).
*   **Salida:** Almacena los datos crudos en la colección `eventos` de la base de datos `waze_db` en MongoDB (servicio `storage`).
*   **Configuración:** El número máximo de eventos a recolectar (`MAX_EVENTS_TO_COLLECT`) se puede configurar en `docker-compose.yml`.

#### 2. Mongo Exporter (Extracción y Enriquecimiento)
*   **Ubicación:** `mongo_exporter/`
*   **Tecnología:** Python, `pymongo`, `shapely`, `csv`, `json`.
*   **Función:**
    *   Lee los datos de la colección `eventos` de MongoDB.
    *   Carga el archivo `comunas_rm.geojson`.
    *   Para cada evento, determina la **comuna** utilizando `shapely` para verificar si el punto de ubicación del evento está contenido en alguno de los polígonos de las comunas.
    *   Parsea el `timestamp_waze` para extraer `hora_del_dia` y `dia_semana`.
    *   Escribe estos datos enriquecidos en el archivo `/pig_input_data/waze_events.tsv` (mapeado desde el volumen del contenedor).
*   **Salida:** Archivo `waze_events.tsv` en `entrega2/pig_processing/data_input/`.

#### 3. Pig Processor (Procesamiento y Análisis)
*   **Ubicación:** `entrega2/pig_processing/`
*   **Tecnología:** Apache Pig 0.17.0, Pig Latin.
*   **Función:**
    *   Lee `waze_events.tsv`.
    *   Realiza filtros (ej. por campos no nulos, comunas válidas).
    *   Estandariza `original_waze_type` a `standardized_type` (ej. 'JAM' -> 'CONGESTION').
    *   Castea `hora_del_dia_str` y `dia_semana_str` a enteros.
    *   Realiza las siguientes agregaciones:
        *   Conteo de eventos por `standardized_type`.
        *   Conteo de eventos por `comuna`.
        *   Conteo de eventos por `hora_del_dia` (ordenado).
        *   Conteo de eventos por `dia_semana` (ordenado).
    *   Guarda la tabla completa de eventos procesados (`all_enriched_events_table`).
*   **Salida:** Múltiples archivos TSV en subcarpetas dentro de `entrega2/pig_processing/data_output/`.

#### 4. Cache Loader (Carga de Resultados a Redis)
*   **Ubicación:** `cache_loader/`
*   **Tecnología:** Python, `redis`, `csv`.
*   **Función:**
    *   Lee los archivos TSV de resultados generados por el `pig_processor` (ej. `count_by_comuna/part-r-00000`).
    *   Se conecta al servicio Redis (`cache`).
    *   Almacena los datos agregados como pares clave-valor en Redis (ej. clave `stats:comuna:Lampa`, valor `12`).
*   **Salida:** Datos cargados en la instancia de Redis.

#### Servicios de Almacenamiento (MongoDB y Redis)
*   **MongoDB (servicio `storage`):** Almacena los datos crudos recolectados por el scraper.
*   **Redis (servicio `cache`):** Almacena los resultados agregados procesados por Pig para acceso rápido.

---

## Verificación de Resultados

1.  **Archivo TSV del Exportador:**
    *   Revisar `ProyectoDistribuidos/entrega2/pig_processing/data_input/waze_events.tsv`.
    *   Debería contener los eventos de MongoDB con las columnas adicionales: `comuna`, `hora_del_dia_str`, `dia_semana_str`.

2.  **Archivos de Salida de Pig:**
    *   Navegar a `ProyectoDistribuidos/entrega2/pig_processing/data_output/`.
    *   Dentro de las subcarpetas (`count_by_standardized_type`, `count_by_comuna`, `count_by_hour`, `count_by_day_of_week`, `all_enriched_events_table`), abrir los archivos `part-r-00000`.
    *   Verificar que los conteos y los datos procesados sean consistentes con la entrada.

3.  **Datos en Redis:**
    *   Conectarse al contenedor de Redis:
        ```bash
        docker exec -it redis_cache_service redis-cli
        ```
    *   Ejecutar comandos para verificar los datos, por ejemplo:
        ```redis
        KEYS stats:*
        GET stats:type:CONGESTION
        GET stats:comuna:Lampa
        GET stats:hour:21
        GET stats:dow:4 
        ```

---

## Justificación de Decisiones de Diseño

*   **Procesamiento de Comuna y Timestamps en Python (Exporter):**
    Debido a que el conector `mongo-hadoop` para Pig está End-of-Life y presenta dificultades de compatibilidad, y dada la complejidad de integrar librerías Python con dependencias C (como `shapely` para geo-procesamiento) directamente en UDFs de Pig/Jython, se tomó la decisión pragmática de realizar el enriquecimiento de datos (determinación de comuna y parseo de timestamps) en el script Python `export_mongo_to_tsv.py`. Este script actúa como un paso de preparación de datos.
*   **Procesamiento Principal en Pig:** Una vez que los datos son ingeridos por Pig desde el archivo TSV (ya enriquecidos), **todo el filtrado subsecuente, la estandarización de tipos de eventos, y los análisis agregados requeridos se realizan íntegramente utilizando Apache Pig**, cumpliendo así con el requisito central de la entrega.
*   **Caché con Redis:** Se utiliza Redis para almacenar los resultados agregados de Pig debido a su velocidad y simplicidad para el almacenamiento clave-valor, lo cual es ideal para proveer datos rápidamente a una futura capa de visualización.

---

## Evaluación de Rendimiento (Ejemplo)

*(Aquí incluirías tu tabla de tiempos y una breve discusión, como lo describimos antes).*

| Métrica                     | Carga: X eventos | Carga: Y eventos |
| :-------------------------- | :--------------- | :--------------- |
| Eventos Exportados (TSV)    | ...              | ...              |
| Tiempo `mongo_exporter`     | ...              | ...              |
| Tiempo `pig_processor`      | ...              | ...              |
| Tiempo `cache_loader`       | ...              | ...              |

**Discusión:**
* *(Breve análisis de los tiempos y cómo escalan).*
* *(Identificación de posibles cuellos de botella).*

---