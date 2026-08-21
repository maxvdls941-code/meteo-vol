import requests
import pandas as pd
from datetime import datetime

# Identifiants Telegram
TELEGRAM_TOKEN = "8998541789:AAFirSkQ969Y0Iyn2vTr4a7QlE24Jn78has"
TELEGRAM_CHAT_ID = "8699172038"

# Coordonnées spot (Andolsheim)
LAT = 48.339278
LON = 7.474208
VILLE = "Epfig"

def deg_vers_rose(deg):
    secteurs = ["N ⬇️", "NE ↙️", "E ⬅️", "SE ↖️", "S ⬆️", "SW ↗️", "W ➡️", "NW ↘️"]
    return secteurs[int((deg + 22.5) / 45) % 8]

def envoyer_notification_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    res = requests.post(url, json=payload)
    return res.status_code == 200

def verifier_meteo_et_alerter():
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}"
           f"&hourly=wind_speed_10m,wind_gusts_10m,wind_direction_10m,wind_speed_180m,precipitation"
           f"&daily=sunrise,sunset&wind_speed_unit=kmh&timezone=Europe%2FParis")

    headers = {"User-Agent": "AlerteVolBot/1.0"}
    res = requests.get(url, headers=headers).json()

    if "hourly" not in res:
        return

    df = pd.DataFrame(res["hourly"])
    df["time"] = pd.to_datetime(df["time"])

    # Filtrage créneaux du jour
    sr = pd.to_datetime(res["daily"]["sunrise"][0])
    ss = pd.to_datetime(res["daily"]["sunset"][0])
    now = pd.Timestamp.now()

    df_jour = df[(df["time"] >= max(now, sr)) & (df["time"] <= ss)]
    creneaux_verts = []

    for _, row in df_jour.iterrows():
        v_sol = row.get("wind_speed_10m", 0)
        rafales = row.get("wind_gusts_10m", v_sol)
        delta_raf = rafales - v_sol
        v_alt = row.get("wind_speed_180m", 0)
        pluie = row.get("precipitation", 0)
        direction = row.get("wind_direction_10m", 0)

        # Critères stricts Vol Optimal
        if v_sol < 12 and delta_raf < 5 and v_alt < 25 and pluie == 0:
            heure = row["time"].strftime("%H:%M")
            rose = deg_vers_rose(direction)
            creneaux_verts.append(
                f"🟢 *{heure}* : Sol {v_sol:.1f} km/h (raf. +{delta_raf:.1f}) | 180m {v_alt:.1f} km/h | Vent {rose}"
            )

    if creneaux_verts:
        message = f"🪂 *ALERTE MÉTÉO VOL — {VILLE}*\n\n"
        message += f"Créneaux favorables prévus aujourd'hui ({now.strftime('%d/%m')}) :\n\n"
        message += "\n".join(creneaux_verts)
        message += "\n\nBon vol ! 🚀"
        
        envoyer_notification_telegram(message)

if __name__ == "__main__":
    verifier_meteo_et_alerter()

