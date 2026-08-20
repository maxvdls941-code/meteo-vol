import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Météo Vol", layout="wide", page_icon="🪂")

# CSS d'optimisation pour écran de smartphone
st.markdown("""
    <style>
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 0.3rem !important;
        padding-right: 0.3rem !important;
    }
    h1 {
        font-size: 1.5rem !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🪂 Decision Maker Vol")

# Recherche de la ville / spot
nom_ville = st.text_input("📍 Ville ou spot :", value="Andolsheim")

# Géocodage via Open-Meteo
lat, lon, nom_emplacement = 48.0614, 7.4147, "Andolsheim"

if nom_ville.strip():
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={nom_ville}&count=1&language=fr&format=json"
        geo_res = requests.get(geo_url).json()
        
        if "results" in geo_res and len(geo_res["results"]) > 0:
            spot = geo_res["results"][0]
            lat = spot["latitude"]
            lon = spot["longitude"]
            region = spot.get("admin1", "")
            pays = spot.get("country", "")
            nom_emplacement = f"{spot['name']} ({region})"
            st.caption(f"🎯 **{nom_emplacement}** (`{lat:.3f}`, `{lon:.3f}`)")
        else:
            st.warning("Ville non trouvée, position par défaut.")
    except Exception:
        st.error("Erreur de recherche.")

# Interrogation API Open-Meteo
url = (
    f"https://api.open-meteo.com/v1/forecast?"
    f"latitude={lat}&longitude={lon}"
    f"&hourly=wind_speed_10m,wind_gusts_10m,wind_direction_10m,wind_speed_180m,wind_direction_180m,precipitation"
    f"&daily=sunrise,sunset"
    f"&wind_speed_unit=kmh"
    f"&timezone=Europe%2FParis"
)

headers = {"User-Agent": "MeteoVolApp/1.0"}

def deg_vers_rose(deg):
    secteurs = ["N ⬇️", "NE ↙️", "E ⬅️", "SE ↖️", "S ⬆️", "SW ↗️", "W ➡️", "NW ↘️"]
    idx = int((deg + 22.5) / 45) % 8
    return secteurs[idx]

try:
    res = requests.get(url, headers=headers)
    data = res.json()
    
    if "hourly" not in data:
        st.error("Données indisponibles.")
    else:
        # Soleils
        if "daily" in data and "sunrise" in data["daily"]:
            lever = pd.to_datetime(data["daily"]["sunrise"][0]).strftime("%H:%M")
            coucher = pd.to_datetime(data["daily"]["sunset"][0]).strftime("%H:%M")
            st.info(f"🌅 {lever}  |  🌇 {coucher}")

        hourly = data["hourly"]
        df = pd.DataFrame(hourly)
        df["time"] = pd.to_datetime(df["time"])
        
        now = pd.Timestamp.now()
        df_future = df[df["time"] >= now]
        if df_future.empty:
            df_future = df
        df_future = df_future.head(12).reset_index(drop=True)

        def analyser_creneau(row, df_context, idx):
            # 1. Vent sol
            v_sol = row.get("wind_speed_10m", 0)
            avis_sol = "🟢" if v_sol < 12 else ("🟠" if v_sol <= 20 else "🔴")

            # 2. Rafales
            rafales = row.get("wind_gusts_10m", v_sol)
            delta = rafales - v_sol
            avis_rafales = "🟢" if delta < 5 else ("🟠" if delta <= 10 else "🔴")

            # 3. Vent 180m
            v_alt = row.get("wind_speed_180m", 0)
            avis_alt = "🟢" if v_alt < 25 else ("🟠" if v_alt <= 35 else "🔴")

            # 4. Direction
            dir_actuelle = row.get("wind_direction_10m", 0)
            prochaines_dirs = df_context.loc[idx:idx+2, "wind_direction_10m"] if "wind_direction_10m" in df_context.columns else []
            diffs = [min(abs(d - dir_actuelle), 360 - abs(d - dir_actuelle)) for d in prochaines_dirs]
            max_diff = max(diffs) if diffs else 0
            avis_dir = "🟢" if max_diff <= 20 else ("🟠" if max_diff <= 90 else "🔴")

            # 5. Pluie
            pluie = row.get("precipitation", 0)
            avis_pluie = "🟢" if pluie == 0 else ("🟠" if pluie < 0.5 else "🔴")

            # Décision
            tous_avis = [avis_sol, avis_rafales, avis_alt, avis_dir, avis_pluie]
            if "🔴" in tous_avis:
                decision = "🔴 NO-GO"
            elif "🟠" in tous_avis:
                decision = "🟠 Prudence"
            else:
                decision = "🟢 Vol"

            rose = deg_vers_rose(dir_actuelle)

            return {
                "Heure": row["time"].strftime("%Hh"),
                "Sol": f"{v_sol:.0f}k {avis_sol}",
                "Raf.": f"+{delta:.0f} {avis_rafales}",
                "180m": f"{v_alt:.0f}k {avis_alt}",
                "Dir.": f"{rose.split()[0]} {avis_dir}",
                "Pluie": f"{pluie:.1f} {avis_pluie}",
                "Avis": decision
            }

        donnees = [analyser_creneau(row, df_future, i) for i, row in df_future.iterrows()]
        df_res = pd.DataFrame(donnees)

        # Synthèse
        p = df_res.iloc[0]
        statut = p["Avis"]
        st.markdown(f"**Prochain créneau ({p['Heure']}) : {statut}**")

        # Coloration des cellules
        def colorier(val):
            v = str(val)
            if "🟢" in v or "Vol" in v:
                return "background-color: #d4edda; color: #155724; font-weight: bold;"
            elif "🟠" in v or "Prudence" in v:
                return "background-color: #fff3cd; color: #856404; font-weight: bold;"
            elif "🔴" in v or "NO-GO" in v:
                return "background-color: #f8d7da; color: #721c24; font-weight: bold;"
            return ""

        styled_df = df_res.style.map(colorier)

        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True
        )

except Exception as e:
    st.error(f"Erreur : {e}")
