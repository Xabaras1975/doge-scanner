import os
import time
import json
import requests
import numpy as np
from datetime import datetime

# ================= CONFIGURAZIONE =================
INSTRUMENT = "DOGE_EUR"
HOLDINGS = 186.49
TIMEFRAME = "1h"
PERIOD = 20
STD_DEV_MULTIPLIER = 2.0
CHECK_INTERVAL_SECONDS = 300     # Controllo ogni 5 minuti
MAX_RUNTIME_SECONDS = 5 * 3600    # 5 ore per sessione
MEMORY_FILE = "doge_memory.json"

# Prezzo di riferimento pre-crollo (29 Ottobre ore 00:00)
PREZZO_BASE_PRE_CROLLO = 0.07280 

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

def carica_memoria():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                dati = json.load(f)
                return dati
        except Exception:
            pass
    return {
        "prezzo_originale": PREZZO_BASE_PRE_CROLLO,
        "data_avvio": "2026-10-29 00:00",
        "last_state": "NORMAL"
    }

def salva_memoria(dati):
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(dati, f, indent=4)
    except Exception as e:
        print(f"Errore salvataggio memoria: {e}")

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

def analyze_and_notify(memoria):
    closes = get_market_data()
    if not closes or len(closes) < PERIOD:
        print("Dati insufficienti o errore API.")
        return memoria

    current_price = closes[-1]
    recent_closes = closes[-PERIOD:]
    sma = np.mean(recent_closes)
    std_dev = np.std(recent_closes)

    upper_band = sma + (STD_DEV_MULTIPLIER * std_dev)
    lower_band = sma - (STD_DEV_MULTIPLIER * std_dev)
    dev_percent = ((current_price - sma) / sma) * 100
    portfolio_val = current_price * HOLDINGS

    prezzo_base = memoria.get("prezzo_originale", PREZZO_BASE_PRE_CROLLO)
    last_state = memoria.get("last_state", "NORMAL")

    diff_pre_crollo = ((current_price - prezzo_base) / prezzo_base) * 100
    segno_diff = "+" if diff_pre_crollo >= 0 else ""

    print(
        f"[{time.strftime('%H:%M:%S')}] Prezzo: €{current_price:.5f} | "
        f"Vs Pre-Crollo (€{prezzo_base:.5f}): {segno_diff}{diff_pre_crollo:.2f}% | "
        f"Controvalore: €{portfolio_val:.2f}"
    )

    current_state = "NORMAL"

    if current_price >= upper_band:
        current_state = "OVERBOUGHT"
        if last_state != "OVERBOUGHT":
            msg = (
                f"🚀 *ALERT TARGET PROFITTO DOGE (+2σ)*\n\n"
                f"• Prezzo Attuale: `€{current_price:.5f}`\n"
                f"• Livello Pre-Crollo: `€{prezzo_base:.5f}`\n"
                f"• Variazione dal Pre-Crollo: *{segno_diff}{diff_pre_crollo:.2f}%*\n"
                f"• Controvalore ({HOLDINGS} DOGE): *€{portfolio_val:.2f}*\n"
                f"• Deviazione Bollinger: *+{dev_percent:.2f}%*\n\n"
                f"💡 _Picco statistico: momento per prendere profitto._"
            )
            send_telegram_alert(msg)

    elif current_price <= lower_band:
        current_state = "OVERSOLD"
        if last_state != "OVERSOLD":
            msg = (
                f"📉 *ALERT ACCUMULO DOGE (-2σ)*\n\n"
                f"• Prezzo Attuale: `€{current_price:.5f}`\n"
                f"• Livello Pre-Crollo: `€{prezzo_base:.5f}`\n"
                f"• Variazione dal Pre-Crollo: *{segno_diff}{diff_pre_crollo:.2f}%*\n"
                f"• Controvalore ({HOLDINGS} DOGE): *€{portfolio_val:.2f}*\n"
                f"• Deviazione Bollinger: *{dev_percent:.2f}%*\n\n"
                f"💡 _Ipervenduto statistico: momento per accumulare._"
            )
            send_telegram_alert(msg)

    memoria["last_price"] = current_price
    memoria["last_state"] = current_state
    memoria["ultimo_aggiornamento"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    salva_memoria(memoria)

    return memoria

def main():
    print(f"Avvio monitoraggio DOGE rispetto al pre-crollo (€{PREZZO_BASE_PRE_CROLLO:.5f})...")
    memoria = carica_memoria()
    start_time = time.time()

    while (time.time() - start_time) < MAX_RUNTIME_SECONDS:
        memoria = analyze_and_notify(memoria)
        time.sleep(CHECK_INTERVAL_SECONDS)

    print("Ciclo di 5 ore completato.")

if __name__ == "__main__":
    main()
