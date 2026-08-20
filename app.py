import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Météo Vol - Decision Maker", layout="wide", page_icon="🪂")

st.title("🪂 Decision Maker — Paramoteur & Vol Libre")

# Recherche de la ville / spot
nom_ville = st.text_input("📍 Rechercher une ville ou un spot de vol :", value="Andolsheim")

# Géocodage via Open-Meteo
lat, lon, nom_emplacement = 48.0614, 7.4147, "Andolsheim (Grand Est, France)"

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
            nom_emplacement = f"{spot['name']} ({region}, {pays})"
            st.success(f"🎯 Localisation : **{nom_emplacement}** — Lat: `{lat:.4f}`, Lon: `{lon:.4f}`")
        else:
            st.warning(f"Aucune localité trouvée pour « {nom_ville} ». Position par défaut retenue.")
    except Exception:
        st.error("Erreur lors de la recherche de la ville. Position par défaut retenue.")

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
    secteurs = [
        "N ⬇️", "NE ↙️", "E ⬅️", "SE ↖️",
        "S ⬆️", "SW ↗️", "W ➡️", "NW ↘️"
    ]
    idx = int((deg + 22.5) / 45) % 8
    return secteurs[idx]

try:
    res = requests.get(url, headers=headers)
    data = res.json()
    
    if "hourly" not in data:
        st.error(f"Erreur du service météo : {data.get('reason', 'Réponse invalide')}")
    else:
        # Affichage du soleil
        if "daily" in data and "sunrise" in data["daily"] and "sunset" in data["daily"]:
            lever_soleil = pd.to_datetime(data["daily"]["sunrise"][0]).strftime("%H:%M")
            coucher_soleil = pd.to_datetime(data["daily"]["sunset"][0]).strftime("%H:%M")
            st.info(f"🌅 **Lever du soleil :** {lever_soleil}  |  🌇 **Coucher du soleil :** {coucher_soleil}")

        hourly = data["hourly"]
        df = pd.DataFrame(hourly)
        df["time"] = pd.to_datetime(df["time"])
        
        now = pd.Timestamp.now()
        df_future = df[df["time"] >= now]
        if df_future.empty:
            df_future = df
        df_future = df_future.head(12).reset_index(drop=True)

        def analyser_creneau(row, df_context, idx):
            heure_str = row["time"].strftime("%H:%M")

            # 1. Vent moyen sol (10 m)
            v_sol = row.get("wind_speed_10m", 0)
            if v_sol < 12:
                avis_sol = "🟢 Vert"
            elif v_sol <= 20:
                avis_sol = "🟠 Orange"
            else:
                avis_sol = "🔴 NO-GO"

            # 2. Écart Rafales
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

            # 4. Évolution direction
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

            # 5. Précipitations
            pluie = row.get("precipitation", 0)
            if pluie == 0:
                avis_pluie = "🟢 Sec"
            elif pluie < 0.5:
                avis_pluie = "🟠 Risque"
            else:
                avis_pluie = "🔴 NO-GO"

            # Synthèse globale
            tous_avis = [avis_sol, avis_rafales, avis_alt, avis_dir, avis_pluie]
            if any("🔴" in a for a in tous_avis):
                decision = "🔴 NO-GO"
            elif any("🟠" in a for a in tous_avis):
                decision = "🟠 Prudence"
            else:
                decision = "🟢 Vol optimal"

            rose = deg_vers_rose(dir_actuelle)

            return {
                "⏱️ Heure": row["time"].strftime("%H:%M (%d/%m)"),
                "💨 Vent sol": f"{v_sol:.1f} km/h",
                "Sol": avis_sol,
                "🌪️ Rafales": f"+{delta_rafales:.1f} km/h",
                "Delta": avis_rafales,
                "🪂 Vent 180m": f"{v_alt:.1f} km/h",
                "Alt.": avis_alt,
                "🧭 Direction": f"{rose} ({dir_actuelle:.0f}°)",
                "Dir. Status": avis_dir,
                "🌧️ Pluie": f"{pluie:.1f} mm/h",
                "Pluie Status": avis_pluie,
                "🚦 Décision": f"{heure_str} — {decision}"
            }

        donnees_analysees = [analyser_creneau(row, df_future, i) for i, row in df_future.iterrows()]
        df_resultats = pd.DataFrame(donnees_analysees)

        # Carte de synthèse au sommet
        prochain = df_resultats.iloc[0]
        statut_prochain = prochain["🚦 Décision"]
        dir_prochaine = prochain["🧭 Direction"]

        if "🟢" in statut_prochain:
            st.success(f"### 🟢 Prochain créneau : {statut_prochain}\n**Vent du secteur :** {dir_prochaine}")
        elif "🟠" in statut_prochain:
            st.warning(f"### 🟠 Prochain créneau : {statut_prochain}\n**Vent du secteur :** {dir_prochaine}")
        else:
            st.error(f"### 🔴 Prochain créneau : {statut_prochain}\n**Vent du secteur :** {dir_prochaine}")

        # Stylisation dynamique
        def colorier_cellule(val):
            val_str = str(val)
            if "🟢" in val_str or "Vol optimal" in val_str or "Sec" in val_str:
                return "background-color: #d4edda; color: #155724; font-weight: bold;"
            elif "🟠" in val_str or "Prudence" in val_str or "Risque" in val_str:
                return "background-color: #fff3cd; color: #856404; font-weight: bold;"
            elif "🔴" in val_str or "NO-GO" in val_str:
                return "background-color: #f8d7da; color: #721c24; font-weight: bold;"
            return ""

        styled_df = df_resultats.style.map(colorier_cellule)

        st.subheader("📊 Prévisions détaillées heure par heure")
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Impossible de récupérer les données météo : {e}")
