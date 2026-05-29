from flask import Flask, request, send_file, render_template_string
from flask_cors import CORS
import edge_tts
import asyncio
import io

app = Flask(__name__)
CORS(app)  # 👈 This allows requests from any website

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

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/download', methods=['POST', 'OPTIONS'])
def download():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.json
    text = data.get('text', '')
    voice = data.get('voice', 'en-US-AriaNeural')

    async def generate():
        communicate = edge_tts.Communicate(text, voice)
        audio = b''
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio += chunk["data"]
        return audio

    audio = asyncio.run(generate())
    return send_file(
        io.BytesIO(audio),
        mimetype='audio/mpeg',
        as_attachment=True,
        download_name='tts.mp3'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)