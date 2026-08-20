import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Météo Vol - Decision Maker", layout="wide", page_icon="🪂")

st.title("🪂 Decision Maker — Paramoteur & Vol Libre")

# --- RECHERCHE DE SPOT ---
nom_ville = st.text_input("📍 Rechercher une ville ou un spot de vol :", value="Andolsheim")
lat, lon, nom_emplacement = 48.0614, 7.4147, "Andolsheim (Grand Est, France)"

if nom_ville.strip():
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={nom_ville}&count=1&language=fr&format=json"
        geo_res = requests.get(geo_url).json()
        if "results" in geo_res and len(geo_res["results"]) > 0:
            spot = geo_res["results"][0]
            lat, lon = spot["latitude"], spot["longitude"]
            nom_emplacement = f"{spot['name']} ({spot.get('admin1', '')}, {spot.get('country', '')})"
            st.success(f"🎯 Localisation : **{nom_emplacement}** — Lat : `{lat:.4f}`, Lon : `{lon:.4f}`")
        else:
            st.warning(f"Aucune localité trouvée pour « {nom_ville} ». Position par défaut retenue.")
    except:
        st.error("Erreur de géocodage.")

# --- CALCUL MÉTÉO ---
url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
       f"&hourly=wind_speed_10m,wind_gusts_10m,wind_direction_10m,wind_speed_180m,wind_direction_180m,precipitation"
       f"&daily=sunrise,sunset&wind_speed_unit=kmh&timezone=Europe%2FParis")

headers = {"User-Agent": "MeteoVolApp/1.0"}

def deg_vers_rose(deg):
    secteurs = ["N ⬇️", "NE ↙️", "E ⬅️", "SE ↖️", "S ⬆️", "SW ↗️", "W ➡️", "NW ↘️"]
    return secteurs[int((deg + 22.5) / 45) % 8]

try:
    res = requests.get(url, headers=headers).json()
    
    if "hourly" in res:
        if "daily" in res and "sunrise" in res["daily"]:
            sr = pd.to_datetime(res["daily"]["sunrise"][0]).strftime("%H:%M")
            ss = pd.to_datetime(res["daily"]["sunset"][0]).strftime("%H:%M")
            st.info(f"🌅 **Lever :** {sr}  |  🌇 **Coucher :** {ss}")

        df = pd.DataFrame(res["hourly"])
        df["time"] = pd.to_datetime(df["time"])
        now = pd.Timestamp.now()
        df_future = df[df["time"] >= now].head(12).reset_index(drop=True)

        def analyser(row, df_context, idx):
            heure_str = row["time"].strftime("%H:%M")
            v_sol = row.get("wind_speed_10m", 0)
            rafales = row.get("wind_gusts_10m", v_sol)
            delta_rafales = rafales - v_sol
            v_alt = row.get("wind_speed_180m", 0)
            pluie = row.get("precipitation", 0)
            dir_actuelle = row.get("wind_direction_10m", 0)

            avis_sol = "🟢 Vert" if v_sol < 12 else ("🟠 Orange" if v_sol <= 20 else "🔴 NO-GO")
            avis_raf = "🟢 Vert" if delta_rafales < 5 else ("🟠 Orange" if delta_rafales <= 10 else "🔴 NO-GO")
            avis_alt = "🟢 Vert" if v_alt < 25 else ("🟠 Orange" if v_alt <= 35 else "🔴 NO-GO")
            avis_plu = "🟢 Sec" if pluie == 0 else ("🟠 Risque" if pluie < 0.5 else "🔴 NO-GO")

            tous_avis = [avis_sol, avis_raf, avis_alt, avis_plu]
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
                "Delta": avis_raf,
                "🪂 Vent 180m": f"{v_alt:.1f} km/h",
                "Alt.": avis_alt,
                "🧭 Direction": f"{rose} ({dir_actuelle:.0f}°)",
                "🌧️ Pluie": f"{pluie:.1f} mm/h",
                "Pluie Status": avis_plu,
                "🚦 Décision": f"{heure_str} — {decision}"
            }

        donnees = [analyser(row, df_future, i) for i, row in df_future.iterrows()]
        df_resultats = pd.DataFrame(donnees)

        # Synthèse Vol Optimal
        df_verts = df_resultats[df_resultats["🚦 Décision"].str.contains("Vol optimal", na=False)]
        if not df_verts.empty:
            prochain_vert = df_verts.iloc[0]
            heures_vertes = " | ".join(df_verts["⏱️ Heure"].apply(lambda x: x.split()[0]).tolist())
            st.success(
                f"### 🟢 Prochain créneau optimal : {prochain_vert['🚦 Décision']}\n"
                f"**Vent du secteur :** {prochain_vert['🧭 Direction']}\n\n"
                f"✨ **Créneaux vol optimal à venir :** {heures_vertes}"
            )
        else:
            prochain = df_resultats.iloc[0]
            st.warning(f"### ⚠️ Prochain créneau : {prochain['🚦 Décision']}\n**Vent du secteur :** {prochain['🧭 Direction']}")

        # Style du tableau
        def colorier_cellule(val):
            val_str = str(val)
            if "🟢" in val_str or "Vol optimal" in val_str or "Sec" in val_str:
                return "background-color: #d4edda; color: #155724; font-weight: bold;"
            elif "🟠" in val_str or "Prudence" in val_str or "Risque" in val_str:
                return "background-color: #fff3cd; color: #856404; font-weight: bold;"
            elif "🔴" in val_str or "NO-GO" in val_str:
                return "background-color: #f8d7da; color: #721c24; font-weight: bold;"
            return ""

        st.subheader("📊 Prévisions détaillées heure par heure")
        st.dataframe(df_resultats.style.map(colorier_cellule), use_container_width=True, hide_index=True)

        # --- CONDENSÉ ESPACES AÉRIENS (SOUS LE TABLEAU) ---
        st.markdown("---")
        st.subheader("🗺️ Repères Espace Aérien & Sécurité (Colmar / Andolsheim)")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            **🟢 Classe d'espace & Plafonds**
            * **Sol** : Classe G (Espace non contrôlé).
            * **Plafond VFR Plaine** : TMA Bâle/Strasbourg à **2500 ft / 3500 ft AMSL** (~750m - 1000m).
            """)
        with col2:
            st.markdown("""
            **✈️ Aérodrome Colmar LFGA (~6km NO)**
            * **Vigilance** : Approches IFR + largages parachutistes.
            * **Fréquences** : Auto-info `125.850 MHz` | Vol libre `123.500 MHz`.
            """)
        with col3:
            st.markdown("""
            **🌲 Reliefs & Frontière**
            * **Vosges (PNR)** : Min. **1000 ft (300m) sol** sur zones protégées.
            * **Le Rhin (~12km E)** : Limite FIR France / Allemagne.
            """)

        st.caption("🔗 Liens utiles : [Carte OACI VFR Géoportail](https://www.geoportail.gouv.fr/carte?c=7.4147,48.0614&z=12&l0=GEOGRAPHICALGRIDSSYSTEMS.MAPS.SCAN-OACI::GEOPORTAIL:OGC:WMTS(1)&permalink=no) | [NOTAM SIA Aviation Civile](https://www.sia.aviation-civile.gouv.fr)")

except Exception as e:
    st.error(f"Erreur de chargement météo : {e}")
