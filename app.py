from datetime import datetime
import requests
import streamlit as st

st.set_page_config(page_title="Météo Vol", page_icon="📍", layout="centered")

# Cache de 30 minutes (1800s) pour éviter les erreurs de quota API
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_weather(lat: float, lon: float):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "wind_speed_10m", "wind_direction_10m"],
        "hourly": ["wind_speed_10m", "wind_direction_10m", "precipitation"],
        "timezone": "auto"
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

# Cache de 24h pour la géolocalisation d'une ville
@st.cache_data(ttl=86400, show_spinner=False)
def geocode_location(location_name: str):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": location_name, "count": 1, "language": "fr"}
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    results = response.json().get("results")
    if results:
        return results[0]["latitude"], results[0]["longitude"], results[0]["name"]
    return None

# --- Interface utilisateur ---

st.selectbox("🔄 Auto-rafraîchissement", ["5 minutes", "15 minutes", "30 minutes"], index=2)

now_str = datetime.now().strftime("%H:%M:%S")
st.info(f"🕒 **Dernière actualisation :** {now_str}")

st.header("🔍 Ajouter un lieu personnalisé")
custom_place = st.text_input("Entre une ville ou un lieu :", placeholder="Ex: Colmar, Cernay, Uffholtz...")

# Liste des spots
spots = [
    {"name": "Aventure Mulhouse (Terciel)", "lat": 47.7483, "lon": 7.3347},
    {"name": "Epfig", "lat": 48.3586, "lon": 7.4636},
]

# Ajout d'un spot recherché dans la liste
if custom_place.strip():
    geo_data = geocode_location(custom_place.strip())
    if geo_data:
        lat, lon, name = geo_data
        spots.insert(0, {"name": name, "lat": lat, "lon": lon})
    else:
        st.warning(f"Lieu introuvable : {custom_place}")

# Affichage des cartes météo
for spot in spots:
    st.subheader(f"📍 {spot['name']}")
    try:
        data = fetch_weather(spot["lat"], spot["lon"])
        current = data.get("current", {})
        
        temp = current.get("temperature_2m")
        wind_speed = current.get("wind_speed_10m")
        wind_dir = current.get("wind_direction_10m")
        
        st.write(f"• **Température :** {temp} °C")
        st.write(f"• **Vent :** {wind_speed} km/h (direction {wind_dir}°)")
    except Exception:
        st.error("Erreur météo.")
