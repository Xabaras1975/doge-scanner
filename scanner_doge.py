import os
import time
import requests
import numpy as np

# Configurazione parametri
INSTRUMENT = "DOGE_EUR"
HOLDINGS = 186.49
TIMEFRAME = "1h"
PERIOD = 20
STD_DEV_MULTIPLIER = 2.0
CHECK_INTERVAL_SECONDS = 300  # Controllo ogni 5 minuti
MAX_RUNTIME_SECONDS = 5 * 3600  # Gira per 5 ore consecutive

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(message: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Credenziali Telegram non configurate.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("Alert Telegram inviato con successo.")
        else:
            print(f"Errore invio Telegram: {res.text}")
    except Exception as e:
        print(f"Eccezione Telegram: {e}")

def get_market_data():
    url = f"https://api.crypto.com/v2/public/get-candlestick?instrument_name={INSTRUMENT}&timeframe={TIMEFRAME}"
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        if data.get("code") == 0 and "data" in data["result"]:
            candlesticks = data["result"]["data"]
            closes = [float(c["c"]) for c in candlesticks]
            return closes
    except Exception as e:
        print(f"Errore scaricamento dati Crypto.com: {e}")
    return None

def analyze_and_notify(last_state):
    closes = get_market_data()
    if not closes or len(closes) < PERIOD:
        print("Dati insufficienti o errore API.")
        return last_state

    current_price = closes[-1]
    recent_closes = closes[-PERIOD:]
    sma = np.mean(recent_closes)
    std_dev = np.std(recent_closes)

    upper_band = sma + (STD_DEV_MULTIPLIER * std_dev)
    lower_band = sma - (STD_DEV_MULTIPLIER * std_dev)
    dev_percent = ((current_price - sma) / sma) * 100
    portfolio_val = current_price * HOLDINGS

    print(f"[{time.strftime('%H:%M:%S')}] Prezzo: €{current_price:.5f} | Media: €{sma:.5f} | Range: [€{lower_band:.5f} - €{upper_band:.5f}]")

    current_state = "NORMAL"

    if current_price >= upper_band:
        current_state = "OVERBOUGHT"
        if last_state != "OVERBOUGHT":
            msg = (
                f"🚀 *ALERT TARGET PROFITTO DOGE (+2σ)*\n\n"
                f"Prezzo Attuale: `€{current_price:.5f}`\n"
                f"Controvalore Saldo: *€{portfolio_val:.2f}*\n"
                f"Deviazione dalla media: *+{dev_percent:.2f}%*\n\n"
                f"💡 _Picco statistico: momento per prendere profitto._"
            )
            send_telegram_alert(msg)

    elif current_price <= lower_band:
        current_state = "OVERSOLD"
        if last_state != "OVERSOLD":
            msg = (
                f"📉 *ALERT ACCUMULO DOGE (-2σ)*\n\n"
                f"Prezzo Attuale: `€{current_price:.5f}`\n"
                f"Controvalore Saldo: *€{portfolio_val:.2f}*\n"
                f"Deviazione dalla media: *{dev_percent:.2f}%*\n\n"
                f"💡 _Ipervenduto statistico: momento per accumulare._"
            )
            send_telegram_alert(msg)

    return current_state

def main():
    print(f"Avvio monitoraggio continuo DOGE (Controllo ogni {CHECK_INTERVAL_SECONDS // 60} minuti)...")
    start_time = time.time()
    last_state = "NORMAL"

    while (time.time() - start_time) < MAX_RUNTIME_SECONDS:
        last_state = analyze_and_notify(last_state)
        time.sleep(CHECK_INTERVAL_SECONDS)

    print("Finestra di 5 ore completata. Riavvio al ciclo successivo.")

if __name__ == "__main__":
    main()
