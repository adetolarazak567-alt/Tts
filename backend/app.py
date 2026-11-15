from flask import Flask, request, send_file, render_template_string, jsonify
from flask_cors import CORS
import edge_tts
import asyncio
import io
import os

app = Flask(__name__)

# 🔒 Lock CORS down — replace "*" with your real frontend origin(s) in production.
# For quick testing you can leave it as "*", but it exposes your backend to abuse.
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
CORS(app, resources={r"/*": {"origins": ALLOWED_ORIGINS}})

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

            if (!resp.ok) {
                const err = await resp.text();
                alert('TTS failed: ' + err);
                return;
            }

            const blob = await resp.blob();
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'tts.mp3';
            a.click();
            URL.revokeObjectURL(a.href);
        });
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_PAGE)


@app.route('/health')
def health():
    """Simple health check for Render."""
    return {"status": "ok"}


async def _generate_audio(text: str, voice: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice)
    audio = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]
    return audio


def generate_audio_sync(text: str, voice: str) -> bytes:
    """
    Safely run the async edge-tts generator from a sync Flask view.
    Creates a fresh event loop per request so it never collides with
    Gunicorn's loop (avoids 'asyncio.run() cannot be called from a
    running event loop').
    """
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_generate_audio(text, voice))
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()


@app.route('/download', methods=['POST'])
def download():
    data = request.get_json(silent=True) or {}

    text = (data.get("text") or "").strip()
    voice = (data.get("voice") or "en-US-AriaNeural").strip()

    # --- Input validation ---
    if not text:
        return jsonify({"error": "text is required"}), 400
    if len(text) > 5000:
        return jsonify({"error": "text too long (max 5000 chars)"}), 400

    # --- Generate audio with clean error reporting ---
    try:
        audio = generate_audio_sync(text, voice)
    except Exception as e:
        app.logger.exception("TTS generation failed")
        return jsonify({"error": f"TTS failed: {type(e).__name__}: {e}"}), 502

    if not audio:
        return jsonify({"error": "TTS returned empty audio"}), 502

    return send_file(
        io.BytesIO(audio),
        mimetype="audio/mpeg",
        as_attachment=True,
        download_name="tts.mp3",
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))