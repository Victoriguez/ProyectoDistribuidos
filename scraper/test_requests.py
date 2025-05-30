import requests

# Coordenadas específicas para un sector de la Región Metropolitana
top = -33.48962998259279
bottom = -33.507774008583155
left = -70.79737901687623
right = -70.776264667511
types = 'alerts,traffic,users'

url = f"https://www.waze.com/live-map/api/georss?top={top}&bottom={bottom}&left={left}&right={right}&env=row&types={types}"

print("Consultando Waze API...")
try:
    response = requests.get(url)
    if response.status_code == 200:
        print("Respuesta recibida:")
        print(response.text[:2000])  # Mostramos solo los primeros 2000 caracteres para no saturar consola
    else:
        print(f"Error HTTP: {response.status_code}")
except requests.RequestException as e:
    print(f"Error en la solicitud: {e}")
