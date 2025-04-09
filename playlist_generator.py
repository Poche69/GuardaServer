import time
import requests
import threading
import json
from datetime import datetime
from flask import Response
from concurrent.futures import ThreadPoolExecutor, as_completed

# Cache globale della playlist
playlist_cache = "#EXTM3U\n"
lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=10)

# Configurazione
UPDATE_INTERVAL = 120  # secondi tra un aggiornamento e l'altro
REQUEST_TIMEOUT = 5    # timeout delle richieste
RAI_USER_AGENT = 'rainet/4.0.5'  # user-agent per i link RAI

def resolve_rai_link(url):
    try:
        response = requests.get(
            url,
            headers={'User-Agent': RAI_USER_AGENT},
            allow_redirects=True,
            timeout=REQUEST_TIMEOUT
        )
        if response.status_code == 200 and response.text.startswith('#EXTM3U'):
            return response.url
    except requests.RequestException as e:
        print(f"[!] Errore RAI: {str(e)}")
    return None

def check_channel(channel):
    name, url = channel.get('name'), channel.get('url')
    if not name or not url:
        return None

    if "rai.it/relinker" in url:
        url = resolve_rai_link(url)
        if not url:
            print(f"[X] RAI {name} non disponibile")
            return None

    try:
        response = requests.head(url, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return f"#EXTINF:-1,{name}\n{url}"
    except requests.RequestException as e:
        print(f"[!] {name} errore: {str(e)}")
    return None

def update_playlist():
    global playlist_cache

    try:
        with open('csvjson.json', 'r', encoding='utf-8') as f:
            channels = json.load(f)
        print(f"[DEBUG] Canali caricati: {len(channels)}")
    except (IOError, json.JSONDecodeError) as e:
        print(f"[!] Errore caricamento file JSON: {str(e)}")
        return

    lines = ['#EXTM3U']
    futures = [executor.submit(check_channel, ch) for ch in channels]

    for future in as_completed(futures):
        if (result := future.result()):
            lines.append(result)

    with lock:
        playlist_cache = '\n'.join(lines)

    print(f"[✓] Playlist aggiornata - {datetime.now().strftime('%H:%M:%S')}")

def update_playlist_loop():
    while True:
        update_playlist()
        time.sleep(UPDATE_INTERVAL)

def start_background_updater():
    print(f"[✓] Avvio background updater - {datetime.now().isoformat()}")
    update_playlist()  # Aggiorna subito all'avvio
    updater = threading.Thread(target=update_playlist_loop, daemon=True)
    updater.start()
