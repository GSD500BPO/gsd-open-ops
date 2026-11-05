"""venv: fast transcript of one roleplay answer (faster-whisper small, int8). Prints JSON {text, duration}."""
import sys, json, os, subprocess, numpy as np
src = sys.argv[1]
raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', src, '-ac', '1', '-ar', '16000', '-f', 's16le', '-'], capture_output=True, timeout=120).stdout
audio = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
dur = len(audio) / 16000
if dur < 1.0:
    print(json.dumps({'text': '', 'duration': round(dur, 1)})); sys.exit(0)
from faster_whisper import WhisperModel
here = os.path.dirname(os.path.abspath(__file__))
m = WhisperModel(os.environ.get('TALENT_WHISPER', 'small'), device='cpu', compute_type='int8', cpu_threads=int(os.environ.get('TALENT_SPEECH_THREADS', '4')),
                 download_root=os.path.join(os.environ.get('TALENT_MODELS', os.path.join(here, '.models')), 'whisper'))
segs, _ = m.transcribe(audio, language='en', beam_size=3, vad_filter=False, condition_on_previous_text=False, temperature=0.0)
print(json.dumps({'text': ' '.join(s.text.strip() for s in segs).strip(), 'duration': round(dur, 1)}))
