from flask import Flask, request, send_file, render_template_string
from flask_cors import CORS
import edge_tts
import asyncio
import io
import re

app = Flask(__name__)
CORS(app)

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>TTS</title>
</head>
<body>
    <h2>Backend is running</h2>
    <form id="ttsForm">
        <textarea id="text" rows="4">Hello</textarea>
        <button type="submit">Download MP3</button>
    </form>
    <script>
        document.getElementById('ttsForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const text = document.getElementById('text').value;
            const resp = await fetch('/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            const blob = await resp.blob();
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'tts.mp3';
            a.click();
        });
    </script>
</body>
</html>
"""

def escape_ssml(text):
    """Escape special XML characters for SSML safety."""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&apos;')
    return text

def build_ssml(text, speed, pitch):
    """
    Build SSML with prosody controls.
    speed: float (0.5 to 2.0)
    pitch: int (-20 to +20)
    """
    # Escape text for XML safety
    safe_text = escape_ssml(text)
    
    # Convert speed to percentage string for SSML rate
    # Edge-TTS accepts: "slow", "medium", "fast", or "50%", "100%", "150%"
    rate_percent = int(speed * 100)
    rate_str = f"{rate_percent}%"
    
    # Convert pitch to SSML format
    # Edge-TTS pitch: "x-low", "low", "default", "high", "x-high", or "-20%", "+20%"
    if pitch == 0:
        pitch_str = "default"
    else:
        pitch_str = f"{pitch:+d}%"
    
    # Build SSML
    ssml = f'<speak><prosody pitch="{pitch_str}" rate="{rate_str}">{safe_text}</prosody></speak>'
    return ssml

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
    pitch = int(data.get('pitch', 0))

    # Validate inputs
    if not text or not text.strip():
        return {'error': 'Text is required'}, 400
    
    # Clamp values for safety
    speed = max(0.5, min(2.0, speed))
    pitch = max(-20, min(20, pitch))

    # Build SSML with pitch and speed
    ssml_text = build_ssml(text, speed, pitch)
    print(f"[TTS] Voice: {voice} | Speed: {speed}x | Pitch: {pitch} | SSML: {ssml_text[:100]}...")

    async def generate():
        communicate = edge_tts.Communicate(ssml_text, voice)
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
