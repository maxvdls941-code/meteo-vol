import os
import requests
import pandas as pd

# Récupération des secrets configurés sur GitHub Actions
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Liste des spots surveillés (Andolsheim remplacé par Aventure Mulhouse Terciel)
SPOTS = [
    {"name": "Aventure Mulhouse (Terciel)", "lat": 47.8180, "lon": 7.1200},
    {"name": "Epfig", "lat": 48.3582, "lon": 7.4636}
]

def get_cardinal(deg):
    dirs = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
    idx = int((deg + 22.5) // 45) % 8
    return dirs[idx]

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Erreur: TELEGRAM_TOKEN ou TELEGRAM_CHAT_ID non définis.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    res = requests.post(url, json=payload)
    if res.status_code != 200:
        print(f"Erreur envoi Telegram: {res.text}")

def check_meteo():
    for spot in SPOTS:
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={spot['lat']}&longitude={spot['lon']}"
               f"&hourly=wind_speed_10m,wind_gusts_10m,wind_direction_10m,wind_speed_180m,precipitation"
               f"&daily=sunrise,sunset&wind_speed_unit=kmh&timezone=Europe%2FParis")
        
        res = requests.get(url).json()
        if "hourly" not in res:
            continue

        df = pd.DataFrame(res["hourly"])
        df["time"] = pd.to_datetime(df["time"])
        sr = pd.to_datetime(res["daily"]["sunrise"][0])
        ss = pd.to_datetime(res["daily"]["sunset"][0])
        now = pd.Timestamp.now(tz="Europe/Paris").tz_localize(None)

        df_jour = df[(df["time"] >= max(now, sr)) & (df["time"] <= ss)]
        creneaux = []

        for _, row in df_jour.iterrows():
            v_sol = row.get("wind_speed_10m", 0)
            rafales = row.get("wind_gusts_10m", v_sol)
            delta_raf = rafales - v_sol
            v_alt = row.get("wind_speed_180m", 0)
            pluie = row.get("precipitation", 0)
            dir_deg = row.get("wind_direction_10m", 0)

            # Critères de sécurité
            if v_sol < 12 and delta_raf < 5 and v_alt < 25 and pluie == 0:
                creneaux.append({
                    "heure": row["time"].strftime("%H:%M"),
                    "v_sol": round(v_sol, 1),
                    "delta_raf": round(delta_raf, 1),
                    "v_alt": round(v_alt, 1),
                    "dir": get_cardinal(dir_deg)
                })

        if creneaux:
            date_str = pd.Timestamp.now(tz="Europe/Paris").strftime("%d/%m")
            msg = f"🪂 *ALERTE MÉTÉO VOL — {spot['name']}*\n\n"
            msg += f"Créneaux favorables prévus aujourd'hui ({date_str}) :\n\n"
            for c in creneaux:
                msg += f"🟢 *{c['heure']}* : Sol {c['v_sol']} km/h (raf. +{c['delta_raf']}) | 180m {c['v_alt']} km/h | Vent {c['dir']}\n"
            msg += "\nBon vol ! 🚀"
            send_telegram(msg)

if __name__ == "__main__":
    check_meteo()
