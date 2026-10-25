import os
import requests
import numpy as np
import pandas as pd
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

DOGE_QUANTITA = 186.49
VALUTA_TARGET = "DOGE_EUR"

def invia_telegram(messaggio):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[ERRORE] Credenziali Telegram non trovate nelle variabili d'ambiente.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": messaggio, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        print(f"Esito invio Telegram: {r.status_code}")
    except Exception as e:
        print(f"Errore invio Telegram: {e}")

def fetch_crypto_com_ticker(symbol="DOGE_EUR"):
    url = "https://api.crypto.com/v2/public/get-ticker"
    params = {"instrument_name": symbol}
    try:
        res = requests.get(url, params=params, timeout=10).json()
        if res.get("code") == 0:
            data_raw = res["result"]["data"]
            data = data_raw[0] if isinstance(data_raw, list) else data_raw
            return float(data.get("a", 0)), float(data.get("b", 0)), float(data.get("k", 0))
    except Exception as e:
        print(f"Errore ticker: {e}")
    return None, None, None

def fetch_crypto_candlesticks(symbol="DOGE_EUR", timeframe="1h"):
    url = "https://api.crypto.com/v2/public/get-candlestick"
    params = {"instrument_name": symbol, "timeframe": timeframe}
    try:
        res = requests.get(url, params=params, timeout=10).json()
        if res.get("code") == 0:
            data_raw = res["result"]["data"]
            data_list = data_raw if isinstance(data_raw, list) else data_raw.get("data", [])
            df = pd.DataFrame(data_list)
            if not df.empty and 'c' in df.columns:
                df['c'] = df['c'].astype(float)
                return df['c'].values
    except Exception as e:
        print(f"Errore candele: {e}")
    return np.array([])

def analizza_doge():
    ask, bid, last_price = fetch_crypto_com_ticker(VALUTA_TARGET)
    closes = fetch_crypto_candlesticks(VALUTA_TARGET, timeframe="1h")
    
    if last_price is None or len(closes) < 20:
        print("Dati di mercato non disponibili temporaneamente.")
        return

    valore_attuale_eur = round(DOGE_QUANTITA * last_price, 2)
    finestra = closes[-20:]
    media = np.mean(finestra)
    std = np.std(finestra)
    banda_superiore = media + (2.0 * std)
    banda_inferiore = media - (2.0 * std)
    deviazione_pct = round(((last_price - media) / media) * 100, 2)

    print("=" * 60)
    print("🐶 MONITOR QUANTITATIVO DOGE/EUR")
    print(f"Prezzo Corrente: €{last_price:.5f} | Valore Saldo: €{valore_attuale_eur:.2f}")
    print(f"Media (20h): €{media:.5f} | Deviazione: {deviazione_pct}%")
    print(f"Soglia Sell (Banda Sup +2σ): €{banda_superiore:.5f}")
    print(f"Soglia Buy  (Banda Inf -2σ): €{banda_inferiore:.5f}")
    print("=" * 60)

    if last_price >= banda_superiore:
        msg = (
            f"🚀 <b>ALERT TARGET PROFITTO DOGE (+2σ)</b>\n\n"
            f"Prezzo Attuale: <code>€{last_price:.5f}</code>\n"
            f"Controvalore Saldo: <b>€{valore_attuale_eur:.2f}</b>\n"
            f"Deviazione dalla media: <b>+{deviazione_pct}%</b>\n\n"
            f"💡 <i>Picco statistico: momento per prendere profitto.</i>"
        )
        invia_telegram(msg)
    elif last_price <= banda_inferiore:
        msg = (
            f"📉 <b>ALERT ACCUMULO DOGE (-2σ)</b>\n\n"
            f"Prezzo Attuale: <code>€{last_price:.5f}</code>\n"
            f"Controvalore Saldo: <b>€{valore_attuale_eur:.2f}</b>\n"
            f"Deviazione dalla media: <b>{deviazione_pct}%</b>\n\n"
            f"💡 <i>Ipervenduto statistico: momento per accumulare.</i>"
        )
        invia_telegram(msg)
    else:
        print("Prezzo all'interno del canale ordinario. Nessun alert inviato.")

if __name__ == "__main__":
    analizza_doge()
