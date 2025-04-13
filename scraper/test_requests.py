import requests

# Definir los parámetros
top = -33.48962998259279
bottom = -33.507774008583155
left = -70.79737901687623
right = -70.776264667511
types = 'alerts,traffic,users'

# Construir la URL
url = f"https://www.waze.com/live-map/api/georss?top={top}&bottom={bottom}&left={left}&right={right}&env=row&types={types}"

print("📡 Consultando Waze API...")
response = requests.get(url)

if response.status_code == 200:
    print("✅ Respuesta recibida:")
    print(response.text[:2000])  # Imprimir los primeros 2000 caracteres
else:
    print(f"❌ Error al consultar: {response.status_code}")
