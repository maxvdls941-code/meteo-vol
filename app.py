from datetime import datetime
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Météo Vol ULM", page_icon="🪂", layout="centered")

# Liste des jours en français (garantit le bon affichage sur les serveurs distants)
JOURS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

# Cache de 30 minutes (1800s) pour éviter les blocages API
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_weather(lat: float, lon: float, days: int = 3):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"],
        "hourly": ["temperature_2m", "wind_speed_10m", "wind_gusts_10m", "precipitation", "wind_direction_10m"],
        "forecast_days": days,
        "timezone": "auto"
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

# Cache de 24h pour la géolocalisation
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

# --- En-tête ---

col_header, col_refresh = st.columns([2, 1])
with col_header:
    st.title("🪂 Météo Vol ULM")
with col_refresh:
    st.selectbox("Auto-rafraîchissement", ["5 min", "15 min", "30 min"], index=2)

st.caption(f"🕒 **Dernière actualisation :** {datetime.now().strftime('%H:%M:%S')}")

# --- Option : Horizon de prévision ---

horizon = st.radio(
    "📅 **Horizon de prévision :**",
    options=[1, 2, 3],
    format_func=lambda x: f"{x} jour{'s' if x > 1 else ''} ({x * 24}h)",
    horizontal=True
)

# --- Recherche de lieu ---

with st.expander("🔍 **Ajouter un lieu personnalisé**", expanded=False):
    custom_place = st.text_input("Entre une ville ou un lieu :", placeholder="Ex: Colmar, Cernay, Uffholtz...")

spots = [
    {"name": "Aventure Mulhouse (Terciel)", "lat": 47.7483, "lon": 7.3347},
    {"name": "Epfig", "lat": 48.3586, "lon": 7.4636},
]

if custom_place.strip():
    geo_data = geocode_location(custom_place.strip())
    if geo_data:
        lat, lon, name = geo_data
        spots.insert(0, {"name": name, "lat": lat, "lon": lon})
    else:
        st.warning(f"Lieu introuvable : {custom_place}")

st.divider()

# --- Affichage des spots et créneaux horaires ---

for spot in spots:
    st.subheader(f"📍 {spot['name']}")
    try:
        data = fetch_weather(spot["lat"], spot["lon"], days=3)
        current = data.get("current", {})
        
        # Conditions actuelles
        temp = current.get("temperature_2m", "--")
        wind = current.get("wind_speed_10m", 0)
        gusts = current.get("wind_gusts_10m", 0)
        wind_dir = current.get("wind_direction_10m", 0)

        c1, c2, c3 = st.columns(3)
        c1.metric("Température", f"{temp} °C")
        c2.metric("Vent moyen", f"{wind} km/h", delta=f"{wind_dir}°", delta_color="off")
        c3.metric("Rafales", f"{gusts} km/h")

        # Statut instantané
        if wind <= 18 and gusts <= 25:
            st.success("✅ **Conditions actuelles favorables au vol**")
        elif wind <= 22 and gusts <= 30:
            st.warning("⚠️ **Conditions actuelles limites**")
        else:
            st.error("❌ **Conditions actuelles défavorables**")

        # Filtrage et mise en forme selon l'horizon sélectionné
        hourly = data.get("hourly", {})
        df_hourly = pd.DataFrame(hourly)
        df_hourly["time"] = pd.to_datetime(df_hourly["time"])
        
        now = datetime.now()
        nb_heures = horizon * 24
        df_next = df_hourly[df_hourly["time"] >= now].head(nb_heures).copy()

        # Évaluation de la volabilité par heure
        def eval_flight(row):
            w = row["wind_speed_10m"]
            g = row["wind_gusts_10m"]
            p = row["precipitation"]
            if w <= 18 and g <= 25 and p == 0:
                return "🟢 Volable"
            elif w <= 22 and g <= 30 and p == 0:
                return "🟠 Limite"
            else:
                return "🔴 Non volable"

        df_next["Volabilité"] = df_next.apply(eval_flight, axis=1)
        
        # Ajout du nom du jour en français (ex: "Jeudi 27/08 14:00")
        df_next["Nom_Jour"] = df_next["time"].dt.dayofweek.map(lambda x: JOURS_FR[x])
        df_next["Jour & Heure"] = df_next["Nom_Jour"] + " " + df_next["time"].dt.strftime("%d/%m %H:00")
        
        display_df = df_next[["Jour & Heure", "Volabilité", "wind_speed_10m", "wind_gusts_10m", "precipitation", "wind_direction_10m"]].copy()
        display_df.columns = ["Jour & Heure", "Statut", "Vent (km/h)", "Rafales (km/h)", "Pluie (mm)", "Dir. (°)"]

        st.markdown(f"**📅 Prévisions sur {horizon} jour{'s' if horizon > 1 else ''} :**")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    except Exception:
        st.error("Erreur météo.")
    
    st.divider()
