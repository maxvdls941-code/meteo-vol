import requests
import pandas as pd
from datetime import datetime

# Identifiants Telegram
TELEGRAM_TOKEN = "8998541789:AAFirSkQ969Y0Iyn2vTr4a7QlE24Jn78has"
TELEGRAM_CHAT_ID = "8699172038"

# Liste des sites à surveiller
SPOTS = [
    {"name": "Andolsheim", "lat": 48.0614, "lon": 7.4147},
    {"name": "Epfig", "lat": 48.3582, "lon": 7.4636}
]

def envoyer_notification_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def verifier_spot(spot):
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={spot['lat']}&longitude={spot['lon']}"
           f"&hourly=wind_speed_10m,wind_gusts_10m,wind_direction_10m,wind_speed_180m,precipitation"
           f"&daily=sunrise,sunset&wind_speed_unit=kmh&timezone=Europe%2FParis")
    
    res = requests.get(url).json()
    if "hourly" not in res: return

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
            creneaux.append(f"🟢 *{row['time'].strftime('%H:%M')}* : Sol {v_sol:.1f} km/h (raf +{delta_raf:.1f})")

    if creneaux:
        msg = f"🪂 *ALERTE VOL — {spot['name']}*\n\n" + "\n".join(creneaux) + "\n\nBon vol ! 🚀"
        envoyer_notification_telegram(msg)

if __name__ == "__main__":
    for spot in SPOTS:
        verifier_spot(spot)
