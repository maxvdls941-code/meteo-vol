from datetime import datetime
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Météo Vol ULM", page_icon="🪂", layout="centered")

JOURS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

# Conversion direction en degrés vers flèche cardinale
def format_wind_dir(deg):
    if deg is None or pd.isna(deg):
        return "-"
    deg = float(deg) % 360
    dirs = [
        ("⬇️ N", 337.5, 360), ("⬇️ N", 0, 22.5),
        ("↙️ NE", 22.5, 67.5),
        ("⬅️ E", 67.5, 112.5),
        ("↖️ SE", 112.5, 157.5),
        ("⬆️ S", 157.5, 202.5),
        ("↗️ SW", 202.5, 247.5),
        ("➡️ W", 247.5, 292.5),
        ("↘️ NW", 292.5, 337.5)
    ]
    for label, start, end in dirs:
        if start <= deg < end or (start == 337.5 and deg >= 337.5):
            return f"{int(deg)}° {label}"
    return f"{int(deg)}°"

# Cache API 30 minutes
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_weather(lat: float, lon: float, days: int = 3):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"],
        "hourly": [
            "temperature_2m",
            "temperature_180m",
            "wind_speed_10m",
            "wind_gusts_10m",
            "precipitation",
            "wind_direction_10m",
            "wind_speed_180m",
            "wind_direction_180m",
            "shortwave_radiation",
            "cape",
            "cloud_cover_low"
        ],
        "daily": ["sunrise", "sunset"],
        "forecast_days": days,
        "timezone": "auto"
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

# Cache Géocodage 24h
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

# --- Affichage des spots ---

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
        c2.metric("Vent sol (10m)", f"{wind} km/h", delta=format_wind_dir(wind_dir), delta_color="off")
        c3.metric("Rafales", f"{gusts} km/h")

        if wind <= 18 and gusts <= 25:
            st.success("✅ **Conditions actuelles favorables au vol**")
        elif wind <= 22 and gusts <= 30:
            st.warning("⚠️ **Conditions actuelles limites**")
        else:
            st.error("❌ **Conditions actuelles défavorables**")

        # Éphémérides VFR
        daily = data.get("daily", {})
        sunrises = pd.to_datetime(daily.get("sunrise", []))
        sunsets = pd.to_datetime(daily.get("sunset", []))

        # Filtrage horaire
        hourly = data.get("hourly", {})
        df_hourly = pd.DataFrame(hourly)
        df_hourly["time"] = pd.to_datetime(df_hourly["time"])
        
        now = datetime.now()
        end_time = now + pd.Timedelta(days=horizon)
        df_filtered = df_hourly[(df_hourly["time"] >= now) & (df_hourly["time"] <= end_time)].copy()

        # Filtrage VFR Jour (-30 min sunrise / +30 min sunset)
        def is_vfr_daylight(t):
            for sr, ss in zip(sunrises, sunsets):
                vfr_start = sr - pd.Timedelta(minutes=30)
                vfr_end = ss + pd.Timedelta(minutes=30)
                if vfr_start <= t <= vfr_end:
                    return True
            return False

        df_next = df_filtered[df_filtered["time"].apply(is_vfr_daylight)].copy()

        # Évaluation avancée du vol
        def eval_flight(row):
            w10 = row["wind_speed_10m"]
            g10 = row["wind_gusts_10m"]
            p = row["precipitation"]
            w180 = row.get("wind_speed_180m", 0)
            rad = row.get("shortwave_radiation", 0)
            cape = row.get("cape", 0)
            clouds = row.get("cloud_cover_low", 0)
            t2 = row.get("temperature_2m", 0)
            t180 = row.get("temperature_180m", 0)
            heure = row["time"].hour

            rejets = []
            if p > 0:
                rejets.append(f"Pluie ({p:.1f} mm)")
            if w10 > 18:
                rejets.append(f"Vent 10m > 18 km/h ({w10:.0f})")
            if g10 > 25:
                rejets.append(f"Rafales > 25 km/h ({g10:.0f})")
            if w180 > 25:
                rejets.append(f"Vent 180m > 25 km/h ({w180:.0f})")
            if clouds > 80:
                rejets.append(f"Nuages bas ({clouds:.0f}%)")
            if (10 <= heure <= 17) and (rad > 350 or cape > 50):
                rejets.append("Risque thermique / Turbulences")

            inversion = (t180 >= t2)

            if not rejets:
                statut = "🟢 Volable" + (" 🧊 Inversion" if inversion else "")
                return statut, "-"
            elif w10 <= 22 and g10 <= 30 and w180 <= 30 and p == 0:
                return "🟠 Limite", ", ".join(rejets)
            else:
                return "🔴 Non volable", ", ".join(rejets)

        eval_res = df_next.apply(eval_flight, axis=1)
        df_next["Volabilité"] = [r[0] for r in eval_res]
        df_next["Cause(s) de rejet"] = [r[1] for r in eval_res]

        df_next["Nom_Jour"] = df_next["time"].dt.dayofweek.map(lambda x: JOURS_FR[x])
        df_next["Jour & Heure"] = df_next["Nom_Jour"] + " " + df_next["time"].dt.strftime("%d/%m %H:00")
        df_next["Dir. Format"] = df_next["wind_direction_10m"].apply(format_wind_dir)

        display_df = df_next[[
            "Jour & Heure",
            "Volabilité",
            "wind_speed_10m",
            "wind_gusts_10m",
            "wind_speed_180m",
            "cloud_cover_low",
            "precipitation",
            "Dir. Format",
            "Cause(s) de rejet"
        ]].copy()
        
        display_df.columns = [
            "Jour & Heure",
            "Statut",
            "Vent 10m (km/h)",
            "Rafales (km/h)",
            "Vent 180m (km/h)",
            "Nuages bas (%)",
            "Pluie (mm)",
            "Dir. Vent",
            "Cause(s) de rejet"
        ]

        # Bulle d'explication des termes (Popover)
        with st.popover("💡 Légende & Explication des termes"):
            st.markdown("""
            **🧊 Inversion thermique (Air lisse) :**
            L'air en altitude (180 m) est plus chaud ou égal à l'air au sol. Cela bloque les mouvements verticaux et garantit un air calme et très stable, idéal pour le vol matinal.

            **☀️ Risque thermique / Turbulences :**
            Entre 10h et 17h, le rayonnement solaire chauffe le sol et crée de fortes ascendances/dégueulantes hachées, même si le vent horizontal reste faible.

            **☁️ Nuages bas (%) :**
            Indique la couverture nuageuse à basse altitude. Supérieur à 80 %, le risque de plafond bas ou de brouillard est élevé.

            **⏱️ Horaires VFR :**
            Les tableaux filtrent automatiquement les heures de nuit et ne conservent que le créneau officiel du **lever du soleil (-30 min)** au **coucher du soleil (+30 min)**.
            """)

        # Configuration des info-bulles sur les colonnes du tableau
        col_config = {
            "Statut": st.column_config.TextColumn(
                "Statut",
                help="🟢 Volable | 🟠 Limite | 🔴 Non volable\n🧊 Inversion : Air très lisse et stable."
            ),
            "Vent 180m (km/h)": st.column_config.NumberColumn(
                "Vent 180m (km/h)",
                help="Gradient de vent en altitude (limite max recommandée : 25 km/h)."
            ),
            "Nuages bas (%)": st.column_config.NumberColumn(
                "Nuages bas (%)",
                help="Couverture à basse altitude (risque de plafond écrasé si > 80%)."
            ),
            "Cause(s) de rejet": st.column_config.TextColumn(
                "Cause(s) de rejet",
                help="Raison(s) précise(s) du classement en Limite ou Non volable."
            )
        }

        # Vues par onglets
        tab_full, tab_best = st.tabs(["📊 Prévisions VFR Jour", "⭐ Meilleurs créneaux (🟢 Volable)"])

        with tab_full:
            st.dataframe(display_df, use_container_width=True, hide_index=True, column_config=col_config)

        with tab_best:
            best_df = display_df[display_df["Statut"].str.contains("🟢 Volable")].copy()
            if not best_df.empty:
                st.dataframe(best_df, use_container_width=True, hide_index=True, column_config=col_config)
            else:
                st.info("Aucun créneau 🟢 parfaitement volable trouvé sur cette période.")

    except Exception:
        st.error("Erreur d'acquisition des données météo.")
    
    st.divider()
