import time
import requests
import threading
import json
from datetime import datetime
from flask import Flask, Response
from concurrent.futures import ThreadPoolExecutor, as_completed
from waitress import serve

app = Flask(__name__)
playlist_cache = "#EXTM3U\n"
lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=10)

# Configurazione
UPDATE_INTERVAL = 120
REQUEST_TIMEOUT = 5
RAI_USER_AGENT = 'rainet/4.0.5'

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

def start_background_updater():
    """Avvia il thread di aggiornamento in background"""
    updater = threading.Thread(target=update_playlist_loop, daemon=True)
    updater.start()

def update_playlist_loop():
    """Loop infinito per aggiornare la playlist"""
    while True:
        update_playlist()
        time.sleep(UPDATE_INTERVAL)

@app.route('/playlist.m3u')
def serve_playlist():
    with lock:
        return Response(playlist_cache, mimetype='audio/x-mpegurl')

if __name__ == '__main__':
    start_background_updater()
    serve(app, host='0.0.0.0', port=10000)
