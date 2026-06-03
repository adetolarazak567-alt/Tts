from flask import Flask, request, send_file, render_template_string
from flask_cors import CORS
import subprocess
import tempfile
import os
import io

app = Flask(__name__)
CORS(app)

HTML_PAGE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>TTS</title></head>
<body><h2>Backend is running</h2></body></html>"""

def escape_xml(text):
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    text = text.replace('"', '&quot;').replace("'", '&apos;')
    return text

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

    if not text or not text.strip():
        return {'error': 'Text is required'}, 400
    
    speed = max(0.5, min(2.0, speed))
    pitch = max(-20, min(20, pitch))

    safe_text = escape_xml(text)
    rate_pct = int(speed * 100)
    pitch_str = "default" if pitch == 0 else f"{pitch:+d}Hz"
    
    # Build SSML
    ssml = f'<speak><prosody pitch="{pitch_str}" rate="{rate_pct}%">{safe_text}</prosody></speak>'
    
    # Write SSML to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ssml', delete=False) as f:
        f.write(ssml)
        ssml_path = f.name
    
    # Output mp3 temp file
    output_path = ssml_path.replace('.ssml', '.mp3')
    
    try:
        # Use edge-tts CLI with --file flag for SSML input
        cmd = [
            'edge-tts',
            '--file', ssml_path,
            '--voice', voice,
            '--write-media', output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"[TTS CLI ERROR] {result.stderr}")
            return {'error': result.stderr}, 500
        
        with open(output_path, 'rb') as f:
            audio = f.read()
        
        # Cleanup
        os.unlink(ssml_path)
        os.unlink(output_path)
        
        return send_file(
            io.BytesIO(audio),
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name='tts.mp3'
        )
        
    except Exception as e:
        # Cleanup on error
        for p in [ssml_path, output_path]:
            if os.path.exists(p):
                os.unlink(p)
        print(f"[TTS ERROR] {e}")
        return {'error': str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
