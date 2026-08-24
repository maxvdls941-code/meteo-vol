import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Météo Vol Paramoteur", page_icon="🪂", layout="wide")

st.title("🪂 Météo Vol Paramoteur")

# Options compactes
col_opt1, col_opt2 = st.columns([2, 1])

with col_opt1:
    afficher_tout = st.checkbox("Afficher toutes les heures (même non volables)", value=True)

with col_opt2:
    auto_refresh_choice = st.selectbox(
        "🔄 Auto-rafraîchissement",
        ["30 minutes", "1 heure", "2 heures", "Désactivé"],
        index=0
    )

# Gestion du minutage pour l'auto-rafraîchissement
refresh_ms_map = {
    "30 minutes": 30 * 60 * 1000,
    "1 heure": 60 * 60 * 1000,
    "2 heures": 120 * 60 * 1000,
    "Désactivé": None
}

refresh_ms = refresh_ms_map[auto_refresh_choice]
if refresh_ms:
    components.html(f"""
        <script>
            setTimeout(function(){{
                window.location.reload();
            }}, {refresh_ms});
        </script>
    """, height=0)

now_str = datetime.now().strftime("%H:%M:%S")
st.info(f"🕒 **Dernière actualisation :** {now_str}")

SPOTS = [
    {"name": "Aventure Mulhouse (Terciel)", "lat": 47.8180, "lon": 7.1200},
    {"name": "Epfig", "lat": 48.3582, "lon": 7.4636}
]

# Champ de recherche de ville
st.markdown("### 🔍 Ajouter un lieu personnalisé")
col_search1, col_search2 = st.columns([3, 1])

with col_search1:
    ville_recherchee = st.text_input("Entre une ville ou un lieu :", placeholder="Ex: Colmar, Cernay, Uffholtz...")

if ville_recherchee:
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={ville_recherchee}&count=1&language=fr&format=json"
    geo_res = requests.get(geo_url).json()
    
    if "results" in geo_res and len(geo_res["results"]) > 0:
        lieu = geo_res["results"][0]
        nom_lieu = f"{lieu['name']} ({lieu.get('admin1', '')})"
        lat_lieu = lieu["latitude"]
        lon_lieu = lieu["longitude"]
        SPOTS.insert(0, {"name": nom_lieu, "lat": lat_lieu, "lon": lon_lieu})
        st.success(f"📍 Lieu trouvé : **{nom_lieu}** ({lat_lieu:.4f}, {lon_lieu:.4f})")
    else:
        st.error("Lieu introuvable. Essaie avec un autre nom de ville.")

def get_cardinal(deg):
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", 
            "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"]
    arrows = ["⬇️", "⬇️", "↙️", "↙️", "⬅️", "⬅️", "↖️", "↖️", 
              "⬆️", "⬆️", "↗️", "↗️", "➡️", "➡️", "↘️", "↘️"]
    idx = int((deg + 11.25) // 22.5) % 16
    return f"{arrows[idx]} {dirs[idx]} ({int(deg)}°)"

def get_plage_horaire(heure_dt):
    h = heure_dt.hour
    if h < 11:
        return "🌅 Matin"
    elif 11 <= h < 17:
        return "☀️ Midi"
    else:
        return "🌇 Soir"

cols = st.columns(len(SPOTS))

for i, spot in enumerate(SPOTS):
    with cols[i]:
        st.subheader(f"📍 {spot['name']}")
        
        # Reconstitution de l'URL valide multi-modèles (support du 180m)
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={spot['lat']}&longitude={spot['lon']}"
               f"&hourly=wind_speed_10m,wind_gusts_10m,wind_direction_10m,wind_speed_180m,precipitation"
               f"&daily=sunrise,sunset&wind_speed_unit=kmh&timezone=Europe%2FParis")
        
        res = requests.get(url).json()
        
        if "hourly" in res:
            df = pd.DataFrame(res["hourly"])
            df["time"] = pd.to_datetime(df["time"])
            sr = pd.to_datetime(res["daily"]["sunrise"][0])
            ss = pd.to_datetime(res["daily"]["sunset"][0])
            now = pd.Timestamp.now()

            df_jour = df[(df["time"] >= max(now, sr)) & (df["time"] <= ss)]
            tableau = []

            for _, row in df_jour.iterrows():
                v_sol = row.get("wind_speed_10m", 0)
                rafales = row.get("wind_gusts_10m", v_sol)
                delta_raf = rafales - v_sol
                v_alt = row.get("wind_speed_180m", 0)
                pluie = row.get("precipitation", 0)
                dir_deg = row.get("wind_direction_10m", 0)

                raisons = []
                if v_sol >= 12:
                    raisons.append("Vent sol (≥ 12)")
                if delta_raf >= 5:
                    raisons.append("Rafales (Δ ≥ 5)")
                if v_alt >= 25:
                    raisons.append("Vent 180m (≥ 25)")
                if pluie > 0:
                    raisons.append("Pluie (> 0)")

                is_volable = (len(raisons) == 0)

                if is_volable or afficher_tout:
                    tableau.append({
                        "Statut": "🟢 OK" if is_volable else "🔴 Non",
                        "Heure": row["time"].strftime("%H:%M"),
                        "Plage": get_plage_horaire(row["time"]),
                        "Sol": round(v_sol, 1),
                        "ΔRaf": round(delta_raf, 1),
                        "180m": round(v_alt, 1),
                        "Dir.": get_cardinal(dir_deg),
                        "Pluie": round(pluie, 1),
                        "Cause du rejet": "—" if is_volable else ", ".join(raisons)
                    })

            if tableau:
                df_res = pd.DataFrame(tableau)
                hauteur_dynamique = (len(df_res) + 1) * 35 + 10
                st.dataframe(df_res, hide_index=True, use_container_width=True, height=hauteur_dynamique)
            else:
                st.warning("Aucun créneau à afficher.")
        else:
            st.error("Erreur météo.")
