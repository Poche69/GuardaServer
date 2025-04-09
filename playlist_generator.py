import time
import requests
import threading
import json
from datetime import datetime
from flask import Flask, Response
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
playlist_cache = "#EXTM3U\n"
lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=10)  # Limita le richieste concorrenti

# Configurazione
UPDATE_INTERVAL = 120  # 2 minuti
REQUEST_TIMEOUT = 5
RAI_USER_AGENT = 'rainet/4.0.5'

def resolve_rai_link(url):
    """Risolvi i link RAI con relinker"""
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
        print(f"[!] Errore RAI per {url}: {str(e)}")
    return None

def check_channel(channel):
    """Verifica se un canale è disponibile e restituisce la riga M3U appropriata"""
    name, url = channel.get('name'), channel.get('url')
    if not name or not url:
        return None

    # Gestione speciale per i link RAI
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
    """Aggiorna la playlist scaricando e verificando tutti i canali"""
    global playlist_cache
    
    try:
        with open('csvjson.json', 'r', encoding='utf-8') as f:
            channels = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"[!] Errore caricamento file JSON: {str(e)}")
        return

    lines = ['#EXTM3U']
    valid_channels = 0
    
    # Usiamo ThreadPoolExecutor per verificare i canali in parallelo
    futures = [executor.submit(check_channel, ch) for ch in channels]
    
    for future in as_completed(futures):
        result = future.result()
        if result:
            lines.append(result)
            valid_channels += 1

    # Aggiorna la cache in modo thread-safe
    with lock:
        playlist_cache = '\n'.join(lines)
    
    print(f"[✓] Playlist aggiornata con {valid_channels} canali - {datetime.now().strftime('%H:%M:%S')}")

def update_playlist_loop():
    """Loop infinito per aggiornare periodicamente la playlist"""
    while True:
        update_playlist()
        time.sleep(UPDATE_INTERVAL)

@app.route('/playlist.m3u')
def serve_playlist():
    """Endpoint per servire la playlist"""
    with lock:
        return Response(playlist_cache, mimetype='audio/x-mpegurl')

if __name__ == '__main__':
    # Avvia il thread di aggiornamento
    updater = threading.Thread(target=update_playlist_loop, daemon=True)
    updater.start()
    
    # Configura Flask
    app.run(host='0.0.0.0', port=5000, threaded=True)
