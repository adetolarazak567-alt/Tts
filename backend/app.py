from flask import Flask, request, send_file, render_template_string
from flask_cors import CORS
import edge_tts
import asyncio
import io

app = Flask(__name__)
CORS(app)

HTML_PAGE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>TTS</title></head>
<body><h2>Backend is running</h2></body></html>"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/download', methods=['POST', 'OPTIONS'])
def download():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.json or {}
    text = data.get('text', '')
    voice = data.get('voice', 'en-US-AriaNeural')
    speed = float(data.get('speed', 1.0))

    if not text or not text.strip():
        return {'error': 'Text is required'}, 400
    
    # Clamp speed
    speed = max(0.5, min(2.0, speed))

    # Edge-TTS uses rate as percentage string
    rate_pct = int(speed * 100)
    
    # Build simple SSML with ONLY rate (speed) - pitch is NOT supported by Edge-TTS
    ssml = f'<speak><prosody rate="{rate_pct}%">{text}</prosody></speak>'
    
    print(f"[TTS] Voice: {voice} | Speed: {speed}x ({rate_pct}%)")

    async def generate():
        communicate = edge_tts.Communicate(ssml, voice)
        audio = b''
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio += chunk["data"]
        return audio

    try:
        audio = asyncio.run(generate())
        return send_file(
            io.BytesIO(audio),
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name='tts.mp3'
        )
    except Exception as e:
        print(f"[TTS ERROR] {e}")
        return {'error': str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
