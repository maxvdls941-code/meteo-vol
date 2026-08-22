import requests
import pandas as pd
from datetime import datetime

# Identifiants Telegram
TELEGRAM_TOKEN = "8998541789:AAFirSkQ969Y0Iyn2vTr4a7QlE24Jn78has"
TELEGRAM_CHAT_ID = "8699172038"

# Coordonnées spot (Epfig par défaut)
# Pour Epfig : LAT = 48.3582, LON = 7.4636
LAT = 48.3582
LON = 7.4636
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
        print("❌ Erreur : impossible de récupérer les données météo.")
        return

    df = pd.DataFrame(res["hourly"])
    df["time"] = pd.to_datetime(df["time"])

    sr = pd.to_datetime(res["daily"]["sunrise"][0])
    ss = pd.to_datetime(res["daily"]["sunset"][0])
    now = pd.Timestamp.now()

    print(f"\n==================================================")
    print(f"   DIAGNOSTIC MÉTÉO POUR {VILLE.upper()}")
    print(f"==================================================")
    print(f"Lever du soleil : {sr.strftime('%H:%M')} | Coucher : {ss.strftime('%H:%M')}\n")

    df_jour = df[(df["time"] >= max(now, sr)) & (df["time"] <= ss)]
    creneaux_verts = []

    for _, row in df_jour.iterrows():
        heure = row["time"].strftime("%H:%M")
        v_sol = row.get("wind_speed_10m", 0)
        rafales = row.get("wind_gusts_10m", v_sol)
        delta_raf = rafales - v_sol
        v_alt = row.get("wind_speed_180m", 0)
        pluie = row.get("precipitation", 0)
        direction = row.get("wind_direction_10m", 0)

        # Test des critères
        raisons_rejet = []
        if v_sol >= 12:
            raisons_rejet.append(f"Vent sol {v_sol:.1f} km/h (max 12)")
        if delta_raf >= 5:
            raisons_rejet.append(f"Rafales +{delta_raf:.1f} km/h (max 5)")
        if v_alt >= 25:
            raisons_rejet.append(f"Vent 180m {v_alt:.1f} km/h (max 25)")
        if pluie > 0:
            raisons_rejet.append(f"Pluie {pluie:.1f} mm")

        if not raisons_rejet:
            rose = deg_vers_rose(direction)
            creneaux_verts.append(
                f"🟢 *{heure}* : Sol {v_sol:.1f} km/h (raf. +{delta_raf:.1f}) | 180m {v_alt:.1f} km/h | Vent {rose}"
            )
            print(f"✅ {heure} : VALIDE (Sol: {v_sol:.1f} km/h, Raf: +{delta_raf:.1f}, 180m: {v_alt:.1f} km/h)")
        else:
            print(f"❌ {heure} : BLOQUÉ -> {', '.join(raisons_rejet)}")

    print(f"\n--------------------------------------------------")
    if creneaux_verts:
        print(f"Bilan : {len(creneaux_verts)} créneau(x) volable(s). Envoi de la notification Telegram...")
        message = f"🪂 *ALERTE MÉTÉO VOL — {VILLE}*\n\n"
        message += f"Créneaux favorables prévus aujourd'hui ({now.strftime('%d/%m')}) :\n\n"
        message += "\n".join(creneaux_verts)
        message += "\n\nBon vol ! 🚀"
        if envoyer_notification_telegram(message):
            print(" Notification Telegram envoyée avec succès !")
        else:
            print("❌ Échec de l'envoi Telegram.")
    else:
        print("Bilan : Aucun créneau ne valide l'ensemble de vos critères.")
        print("Aucun message Telegram n'a été envoyé.")
    print(f"--------------------------------------------------\n")

if __name__ == "__main__":
    verifier_meteo_et_alerter()
