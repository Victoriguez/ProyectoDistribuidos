import requests
import time
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from datetime import datetime

# Conexión a MongoDB
def conectar_mongo():
    print("🔌 Conectando a MongoDB...", flush=True)
    try:
        client = MongoClient('mongodb://storage:27017', serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("✅ Conexión exitosa a MongoDB.", flush=True)
        return client['waze_db']['eventos']
    except ServerSelectionTimeoutError:
        print("❌ No se pudo conectar a MongoDB. ¿Está el contenedor 'storage' activo?", flush=True)
        exit(1)

# Región Metropolitana (coordenadas grandes para cubrir área amplia)
top = -33.3
bottom = -33.7
left = -70.9
right = -70.5
types = 'alerts,traffic,users'
url = f"https://www.waze.com/live-map/api/georss?top={top}&bottom={bottom}&left={left}&right={right}&env=row&types={types}"

def obtener_eventos():
    print("🌐 Consultando Waze Live Map API...", flush=True)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {len(data.get('users', []))} usuarios obtenidos", flush=True)
            return data
        else:
            print(f"❌ Error HTTP al consultar: {response.status_code}", flush=True)
    except requests.RequestException as e:
        print(f"⚠️ Error en la solicitud: {e}", flush=True)
    return None

def guardar_eventos(coleccion, data):
    usuarios = data.get('users', [])
    if usuarios:
        for u in usuarios:
            u['timestamp'] = datetime.now().isoformat()
        print(f"💾 Insertando {len(usuarios)} eventos en MongoDB...", flush=True)
        coleccion.insert_many(usuarios)

if __name__ == '__main__':
    print("🔥 Scraper iniciado.", flush=True)
    coleccion = conectar_mongo()
    eventos_total = 0

    while eventos_total < 10000:
        data = obtener_eventos()
        if data:
            guardar_eventos(coleccion, data)
            eventos_total += len(data.get('users', []))
        time.sleep(5)

    print(f"🎉 Scraper finalizado con {eventos_total} eventos insertados.", flush=True)
