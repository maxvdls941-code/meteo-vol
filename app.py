import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Météo Vol Paramoteur", page_icon="🪂", layout="centered")

st.title("🪂 Météo Vol Paramoteur")
st.caption("Surveillance automatique pour Andolsheim et Epfig")

SPOTS = [
    {"name": "Andolsheim", "lat": 48.0614, "lon": 7.4147},
    {"name": "Epfig", "lat": 48.3582, "lon": 7.4636}
]

if st.button("🔄 Rafraîchir la météo"):
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

        df_jour = df[(df["time"] >= max(now, sr)) & (df["time"] <= ss)]
        creneaux = []

        for _, row in df_jour.iterrows():
            v_sol = row.get("wind_speed_10m", 0)
            rafales = row.get("wind_gusts_10m", v_sol)
            delta_raf = rafales - v_sol
            v_alt = row.get("wind_speed_180m", 0)
            pluie = row.get("precipitation", 0)

            if v_sol < 12 and delta_raf < 5 and v_alt < 25 and pluie == 0:
                creneaux.append({
                    "Heure": row["time"].strftime("%H:%M"),
                    "Vent sol (km/h)": round(v_sol, 1),
                    "Delta Rafales (km/h)": round(delta_raf, 1),
                    "Vent 180m (km/h)": round(v_alt, 1)
                })

        if creneaux:
            st.success(f"{len(creneaux)} créneau(x) volable(s) disponible(s)")
            st.dataframe(pd.DataFrame(creneaux), hide_index=True, use_container_width=True)
        else:
            st.warning("Aucun créneau volable détecté pour le reste de la journée.")
    else:
        st.error("Erreur lors de la récupération des données météo.")
    
    st.divider()
