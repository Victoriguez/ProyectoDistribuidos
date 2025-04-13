import requests
import time
from pymongo import MongoClient
from datetime import datetime

# Conexión a MongoDB (nombre del servicio definido en docker-compose)
client = MongoClient('mongodb://storage:27017')
db = client['waze_db']
coleccion = db['eventos']

# Coordenadas para Región Metropolitana
top = -33.3
bottom = -33.7
left = -70.9
right = -70.5
types = 'alerts,traffic,users'

url = f"https://www.waze.com/live-map/api/georss?top={top}&bottom={bottom}&left={left}&right={right}&env=row&types={types}"

def obtener_eventos():
    print("🌐 Consultando Waze Live Map API...")
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ {len(data.get('users', []))} usuarios obtenidos")
        return data
    else:
        print(f"❌ Error al consultar: {response.status_code}")
        return None

def guardar_eventos(data):
    usuarios = data.get('users', [])
    if usuarios:
        for u in usuarios:
            u['timestamp'] = datetime.now().isoformat()
        print(f"💾 Insertando {len(usuarios)} eventos en MongoDB...")
        coleccion.insert_many(usuarios)

if __name__ == '__main__':
    print("🔥 Scraper está corriendo correctamente.")
    eventos_total = 0
    while eventos_total < 10000:
        data = obtener_eventos()
        if data:
            guardar_eventos(data)
            eventos_total += len(data.get('users', []))
        time.sleep(5)

    print(f"🎉 Se alcanzaron {eventos_total} eventos. Scraper terminado.")
