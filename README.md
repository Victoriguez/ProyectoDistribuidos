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

-   Si deseas limpiar los resultados anteriores de Pig para una nueva ejecución:

    # En PowerShell (Windows)
- Remove-Item -Recurse -Force ./entrega2/pig_processing/data_output/*

    # En Bash (Linux/macOS)
- rm -rf ./entrega2/pig_processing/data_output/*

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