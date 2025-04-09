import time
import requests
import threading
import json
from datetime import datetime
from flask import Flask, Response

app = Flask(__name__)
playlist_cache = "#EXTM3U\n"  # cache iniziale

def resolve_rai_link(url):
    headers = {'User-Agent': 'rainet/4.0.5'}
    try:
        r = requests.get(url, headers=headers, allow_redirects=True, timeout=5)
        if r.status_code == 200 and r.text.startswith('#EXTM3U'):
            return r.url
    except Exception as e:
        print(f"[!] Errore RAI: {e}")
    return None

def update_playlist_loop():
    global playlist_cache
    while True:
        try:
            with open('csvjson.json', 'r', encoding='utf-8') as f:
                channels = json.load(f)

            lines = ['#EXTM3U']
            valid = 0
            for ch in channels:
                name = ch.get('name')
                url = ch.get('url')
                if not name or not url:
                    continue
                if "rai.it/relinker" in url:
                    url = resolve_rai_link(url)
                    if not url:
                        print(f"[X] RAI {name} non disponibile")
                        continue
                try:
                    r = requests.get(url, timeout=5)
                    if r.status_code == 200:
                        lines.append(f'#EXTINF:-1,{name}')
                        lines.append(url)
                        valid += 1
                    else:
                        print(f"[!] {name} offline (code {r.status_code})")
                except Exception as e:
                    print(f"[!] {name} errore: {e}")
            playlist_cache = '\n'.join(lines)
            print(f"[✓] Playlist aggiornata con {valid} canali - {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"[!] Errore aggiornamento playlist: {e}")

        time.sleep(120)  # ogni 2 minuti

@app.route('/playlist.m3u')
def serve_playlist():
    return Response(playlist_cache, mimetype='audio/x-mpegurl')

if __name__ == '__main__':
    thread = threading.Thread(target=update_playlist_loop, daemon=True)
    thread.start()
    app.run(host='0.0.0.0', port=5000)
