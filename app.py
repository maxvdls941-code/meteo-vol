import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Météo Vol - Decision Maker", layout="wide")
st.title("Aide à la décision de vol (Paramoteur / Parapente)")

# Sélection de la position GPS
col1, col2 = st.columns(2)
with col1:
    lat = st.number_input("Latitude", value=48.0614, format="%.4f")
with col2:
    lon = st.number_input("Longitude", value=7.4147, format="%.4f")

# Interrogation de l'API Open-Meteo (10m, rafales, 180m altitude)
url = (
    f"https://api.open-meteo.com/v1/forecast?"
    f"latitude={lat}&longitude={lon}"
    f"&hourly=wind_speed_10m,wind_gusts_10m,wind_direction_10m,wind_speed_180m,wind_direction_180m"
    f"&wind_speed_unit=kmh"
    f"&timezone=Europe%2FParis"
)

headers = {"User-Agent": "MeteoVolApp/1.0"}

try:
    res = requests.get(url, headers=headers)
    data = res.json()
    
    if "hourly" not in data:
        st.error(f"Erreur transmise par le service météo : {data.get('reason', 'Réponse invalide')}")
    else:
        hourly = data["hourly"]
        df = pd.DataFrame(hourly)
        df["time"] = pd.to_datetime(df["time"])
        
        # Filtrer à partir de l'heure actuelle
        now = pd.Timestamp.now()
        df_future = df[df["time"] >= now]
        if df_future.empty:
            df_future = df
        df_future = df_future.head(12).reset_index(drop=True)

        def analyser_creneau(row, df_context, idx):
            # 1. Vent moyen sol (10 m)
            v_sol = row.get("wind_speed_10m", 0)
            if v_sol < 12:
                avis_sol = "🟢 Vert"
            elif v_sol <= 20:
                avis_sol = "🟠 Orange"
            else:
                avis_sol = "🔴 NO-GO"

            # 2. Écart Rafales (Delta = Rafales - Vent moyen)
            rafales = row.get("wind_gusts_10m", v_sol)
            delta_rafales = rafales - v_sol
            if delta_rafales < 5:
                avis_rafales = "🟢 Vert"
            elif delta_rafales <= 10:
                avis_rafales = "🟠 Orange"
            else:
                avis_rafales = "🔴 NO-GO"

            # 3. Vent en altitude (180 m)
            v_alt = row.get("wind_speed_180m", 0)
            if v_alt < 25:
                avis_alt = "🟢 Vert"
            elif v_alt <= 35:
                avis_alt = "🟠 Orange"
            else:
                avis_alt = "🔴 NO-GO"

            # 4. Évolution de la direction
            dir_actuelle = row.get("wind_direction_10m", 0)
            prochaines_dirs = df_context.loc[idx:idx+2, "wind_direction_10m"] if "wind_direction_10m" in df_context.columns else []
            
            diffs = [min(abs(d - dir_actuelle), 360 - abs(d - dir_actuelle)) for d in prochaines_dirs]
            max_diff = max(diffs) if diffs else 0

            if max_diff <= 20:
                avis_dir = "🟢 Vert"
            elif max_diff <= 90:
                avis_dir = "🟠 Orange"
            else:
                avis_dir = "🔴 NO-GO"

            # Synthèse globale
            tous_avis = [avis_sol, avis_rafales, avis_alt, avis_dir]
            if "🔴 NO-GO" in tous_avis:
                decision = "🔴 NO-GO"
            elif "🟠 Orange" in tous_avis:
                decision = "🟠 Prudence"
            else:
                decision = "🟢 Vol optimal"

            return {
                "Heure": row["time"].strftime("%H:%M (%d/%m)"),
                "Vent sol": f"{v_sol:.1f} km/h",
                "Avis Sol": avis_sol,
                "Écart Rafales": f"+{delta_rafales:.1f} km/h",
                "Avis Rafales": avis_rafales,
                "Vent 180m": f"{v_alt:.1f} km/h",
                "Avis 180m": avis_alt,
                "Dir. Sol": f"{dir_actuelle:.0f}° (Δ {max_diff:.0f}°)",
                "Avis Dir.": avis_dir,
                "Décision Globale": decision
            }

        donnees_analysees = [analyser_creneau(row, df_future, i) for i, row in df_future.iterrows()]
        df_resultats = pd.DataFrame(donnees_analysees)

        st.subheader("Analyse heure par heure")
        st.dataframe(df_resultats, use_container_width=True)

except Exception as e:
    st.error(f"Impossible de récupérer les données météo : {e}")
