import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Météo Vol Paramoteur", page_icon="🪂", layout="wide")

st.title("🪂 Météo Vol Paramoteur")
st.caption("Surveillance météo complète pour Aventure Mulhouse et Epfig")

# Options en haut de page
col_opt1, col_opt2 = st.columns([2, 1])

with col_opt1:
    afficher_tout = st.checkbox("Afficher toutes les heures de la journée (même non volables)", value=True)

with col_opt2:
    auto_refresh_choice = st.selectbox(
        "🔄 Auto-rafraîchissement",
        ["30 minutes", "1 heure", "2 heures", "Désactivé"],
        index=0
    )

# Gestion du minutage pour le rafraîchissement automatique
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

# Affichage de l'heure de dernière mise à jour
now_str = datetime.now().strftime("%H:%M:%S")
st.info(f"🕒 **Dernière actualisation des données :** {now_str}")

SPOTS = [
    {"name": "Aventure Mulhouse (Terciel)", "lat": 47.8180, "lon": 7.1200},
    {"name": "Epfig", "lat": 48.3582, "lon": 7.4636}
]

if st.button("🔄 Rafraîchir manuellement"):
    st.rerun()

for spot in SPOTS:
    st.subheader(f"📍 {spot['name']}")
    
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

        # Filtrer de l'heure actuelle (ou du lever du soleil) jusqu'au coucher du soleil
        df_jour = df[(df["time"] >= max(now, sr)) & (df["time"] <= ss)]
        tableau = []

        for _, row in df_jour.iterrows():
            v_sol = row.get("wind_speed_10m", 0)
            rafales = row.get("wind_gusts_10m", v_sol)
            delta_raf = rafales - v_sol
            v_alt = row.get("wind_speed_180m", 0)
            pluie = row.get("precipitation", 0)

            # Analyse des raisons de rejet
            raisons = []
            if v_sol >= 12:
                raisons.append("Vent sol (≥ 12 km/h)")
            if delta_raf >= 5:
                raisons.append("Rafales (Δ ≥ 5 km/h)")
            if v_alt >= 25:
                raisons.append("Vent 180m (≥ 25 km/h)")
            if pluie > 0:
                raisons.append("Pluie (> 0 mm)")

            is_volable = (len(raisons) == 0)

            if is_volable or afficher_tout:
                tableau.append({
                    "Statut": "🟢 OK" if is_volable else "🔴 Non volable",
                    "Heure": row["time"].strftime("%H:%M"),
                    "Vent sol (km/h)": round(v_sol, 1),
                    "Delta Rafales (km/h)": round(delta_raf, 1),
                    "Vent 180m (km/h)": round(v_alt, 1),
                    "Pluie (mm)": round(pluie, 1),
                    "Cause du rejet": "—" if is_volable else ", ".join(raisons)
                })

        if tableau:
            df_res = pd.DataFrame(tableau)
            st.dataframe(df_res, hide_index=True, use_container_width=True)
        else:
            st.warning("Aucun créneau ne correspond aux critères actuels.")
    else:
        st.error("Erreur lors de la récupération des données météo.")
    
    st.divider()
