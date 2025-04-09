from flask import Flask, Response
from playlist_generator import playlist_cache, start_background_updater

app = Flask(__name__)
start_background_updater()  # Avvia subito la generazione e l’updater

@app.route('/')
def index():
    return '🎧 Server playlist attivo.'

@app.route('/playlist.m3u')
def serve_playlist():
    return Response(playlist_cache, mimetype='audio/x-mpegurl')
