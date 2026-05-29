from flask import Flask, request, send_file, render_template_string
import edge_tts
import asyncio
import io

app = Flask(__name__)

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Free TTS</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 2rem auto; padding: 1rem; }
        textarea { width: 100%; height: 100px; padding: 0.5rem; }
        button { padding: 0.5rem 1.5rem; background: #16a34a; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; margin-top: 1rem; }
        #status { margin-top: 1rem; }
    </style>
</head>
<body>
    <h2>🗣️ TTS (MP3 download)</h2>
    <textarea id="text">Hello, this is a test.</textarea>
    <br>
    <button onclick="download()">⬇️ Download MP3</button>
    <div id="status"></div>

    <script>
        async function download() {
            const text = document.getElementById('text').value;
            if (!text) { document.getElementById('status').textContent = 'Please enter text.'; return; }
            document.getElementById('status').textContent = 'Generating... (takes 5-10 seconds)';
            try {
                const resp = await fetch('/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text })
                });
                if (!resp.ok) throw new Error('Server error');
                const blob = await resp.blob();
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = 'tts.mp3';
                a.click();
                document.getElementById('status').textContent = '✅ Downloaded!';
            } catch (err) {
                document.getElementById('status').textContent = '❌ ' + err.message;
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    text = data.get('text', '')
    voice = "en-US-AriaNeural"  # You can add a voice selector later

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
    app.run(host='0.0.0.0', port=10000)  # Render uses port 10000
