#!/usr/bin/env python3
"""Ramón talent pipeline - automatic SPEAKING score for candidate intro videos. 100% local, no paid APIs.

  .venv/bin/python speech_score.py clip.mp4          -> JSON on stdout (logs on stderr)
  from speech_score import score; score(path_or_bytes)

Models (all CPU, downloaded once into .models/):
  - faster-whisper "small" int8 ......... transcript, word timestamps + word confidences, language ID
  - facebook/wav2vec2-base-960h ......... native-English acoustic model: frame confidence + independent transcript
  - Jzuluaga/accent-id-commonaccent_ecapa  accent label + confidence (16 English accents, speechbrain)
  - LanguageTool (local Java server) .... grammar errors per 100 words (LT_SERVER=http://127.0.0.1:8790, or a local JVM)

Scores (0-100):
  clarity  = 0.35*whisper word confidence + 0.25*wav2vec2 frame confidence + 0.40*agreement(whisper vs wav2vec2)
             (agreement = 1 - WER between the two independent transcripts: if a model trained only on native English
              hears the same words Whisper hears, the speech is intelligible)
  fluency  = 0.40*rate (110-170 wpm ideal) + 0.35*pauses + 0.25*fillers, minus 5 per pause > 1.5 s
  grammar  = 100 - 15 * grammar errors per 100 words (capped at 50 if the transcript is garbled)
  neutral_accent = min(clarity, probability mass on US/Canada accent (x1.0) + other native accents (x0.6))
  overall  = 0.35*clarity + 0.25*fluency + 0.25*grammar + 0.15*neutral_accent, capped if too short / not English
  speaking_cefr: >=85 C1, >=75 B2, >=60 B1, >=45 A2, else A1
"""
import gc, json, math, os, re, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.environ.get('TALENT_MODELS', os.path.join(HERE, '.models'))
os.environ.setdefault('HF_HOME', os.path.join(MODELS, 'hf'))
os.environ.setdefault('LTP_PATH', os.path.join(MODELS, 'languagetool'))
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
THREADS = int(os.environ.get('TALENT_SPEECH_THREADS', '4'))
WHISPER_SIZE = os.environ.get('TALENT_WHISPER', 'small')      # fallback: base
VERSION = 'speech-v1 2026-11-01'
MAX_SECONDS = 180                                             # only the first 3 minutes are scored

FILLERS = {'um', 'umm', 'uh', 'uhh', 'uhm', 'er', 'erm', 'ah', 'eh', 'hmm', 'hm', 'mm', 'mhm', 'mmm',
           'este', 'pues', 'bueno', 'eeh', 'ehh'}                 # incl. Spanish fillers common in Colombian speakers
NEUTRAL = {'us': 1.0, 'canada': 1.0, 'england': 0.6, 'australia': 0.6, 'newzealand': 0.6, 'ireland': 0.6,
           'scotland': 0.6, 'wales': 0.6}
GRAMMAR_PENALTY = 15.0                                         # points lost per grammar error / 100 words
ACCENT_SCALE = 30.0                                            # AAM-softmax scale -> probabilities
GRAMMAR_CATS = {'GRAMMAR', 'CONFUSED_WORDS', 'COLLOCATIONS', 'NONSTANDARD_PHRASES'}
# Whisper prompt in a disfluent style so it keeps "um/uh" instead of cleaning them away
PROMPT = "Umm, so, uh, I'm... I mean, like, hmm. Okay, so I have, uh, worked in a call center."

def err(*a): print(*a, file=sys.stderr, flush=True)
def clamp(x, lo=0.0, hi=100.0): return max(lo, min(hi, x))

def to_wav(src):
    """path or bytes -> 16 kHz mono wav file path (temp)."""
    tmpdir = tempfile.mkdtemp(prefix='speech-')
    if isinstance(src, (bytes, bytearray)):
        inp = os.path.join(tmpdir, 'in.bin'); open(inp, 'wb').write(src)
    else:
        inp = src
    out = os.path.join(tmpdir, 'a.wav')
    subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-i', inp, '-t', str(MAX_SECONDS),
                    '-vn', '-ac', '1', '-ar', '16000', '-af', 'highpass=f=60', out], check=True, timeout=120)
    return out, tmpdir

def words_norm(text):
    t = re.sub(r"[^a-z' ]+", ' ', text.lower().replace('-', ' '))
    return [w.strip("'") for w in t.split() if w.strip("'") and w.strip("'") not in FILLERS]

def wer(ref, hyp):
    if not ref: return 1.0 if hyp else 0.0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1] / len(ref)

# ---------------- models ----------------
def run_whisper(audio):
    # audio = float32 numpy @16 kHz (we decode with ffmpeg ourselves; PyAV decoding is avoided on purpose)
    from faster_whisper import WhisperModel
    m = WhisperModel(WHISPER_SIZE, device='cpu', compute_type='int8', cpu_threads=THREADS,
                     download_root=os.path.join(MODELS, 'whisper'))
    lang, lang_p = None, None
    try:
        lang, lang_p, _ = m.detect_language(audio=audio, language_detection_segments=3)
    except Exception as e:
        err('lang detect failed:', e)
    segs, info = m.transcribe(audio, language='en', beam_size=5, word_timestamps=True, initial_prompt=PROMPT,
                              condition_on_previous_text=False, vad_filter=False, temperature=0.0)
    words, text = [], []
    for s in segs:
        text.append(s.text)
        for w in (s.words or []):
            words.append({'w': w.word.strip(), 'start': w.start, 'end': w.end, 'p': w.probability})
    if lang is None: lang, lang_p = info.language, info.language_probability
    del m; gc.collect()
    return ' '.join(t.strip() for t in text).strip(), words, lang, lang_p, info.duration

def run_wav2vec(audio):
    import torch
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
    name = 'facebook/wav2vec2-base-960h'
    proc = Wav2Vec2Processor.from_pretrained(name); model = Wav2Vec2ForCTC.from_pretrained(name).eval()
    blank = proc.tokenizer.pad_token_id
    confs, texts, step = [], [], 16000 * 20
    with torch.no_grad():
        for i in range(0, len(audio), step):
            chunk = audio[i:i + step]
            if len(chunk) < 8000: continue
            iv = proc(chunk, sampling_rate=16000, return_tensors='pt').input_values
            probs = torch.softmax(model(iv).logits[0], dim=-1)
            pmax, ids = probs.max(dim=-1)
            keep = ids != blank
            if keep.any(): confs.extend(pmax[keep].tolist())       # confidence only where a character is emitted
            texts.append(proc.batch_decode(ids.unsqueeze(0))[0])
    del model; gc.collect()
    return (sum(confs) / len(confs) if confs else 0.0), ' '.join(texts).lower()

def run_accent(audio):
    import torch
    from speechbrain.inference.classifiers import EncoderClassifier
    clf = EncoderClassifier.from_hparams(source='Jzuluaga/accent-id-commonaccent_ecapa',
                                         savedir=os.path.join(MODELS, 'accent-ecapa'), run_opts={'device': 'cpu'})
    sig = torch.from_numpy(audio).float()          # already 16 kHz mono (torchaudio.load would need torchcodec)
    win = 16000 * 10; acc = None; n = 0
    with torch.no_grad():
        for i in range(0, max(1, len(sig) - 16000 * 3), win):        # average over 10 s windows
            seg = sig[i:i + win]
            if len(seg) < 16000 * 3: continue
            out = clf.classify_batch(seg.unsqueeze(0))[0][0]
            p = torch.softmax(out * ACCENT_SCALE, dim=-1)        # classifier outputs cosine scores (AAM head)
            acc = p if acc is None else acc + p; n += 1
    if acc is None: return None, 0.0, {}
    acc = (acc / n).tolist()
    labels = [clf.hparams.label_encoder.ind2lab[i] for i in range(len(acc))]
    dist = dict(sorted(zip(labels, acc), key=lambda x: -x[1]))
    del clf; gc.collect()
    top = next(iter(dist))
    return top, dist[top], dist

def run_grammar(text):
    import language_tool_python
    # Prefer ONE long-running LanguageTool server (deploy/languagetool.service). Spawning a JVM per job leaks RAM on small boxes.
    srv = os.environ.get('LT_SERVER', 'http://127.0.0.1:8790')
    tool = language_tool_python.LanguageTool('en-US', remote_server=srv) if srv else language_tool_python.LanguageTool('en-US')
    ms = tool.check(text)
    hits = []
    for m in ms:
        cat = getattr(m, 'category', '') or ''
        rule = getattr(m, 'ruleId', getattr(m, 'rule_id', '')) or ''
        if cat in GRAMMAR_CATS and not rule.startswith(('UPPERCASE', 'EN_QUOTES', 'COMMA', 'WHITESPACE')):
            ctx = getattr(m, 'context', '') or ''
            hits.append({'rule': rule, 'msg': (getattr(m, 'message', '') or '')[:120], 'ctx': ctx[:80]})
    return hits

# ---------------- scoring ----------------
def score(src):
    t0 = time.time()
    try:
        import torch; torch.set_num_threads(THREADS)
    except Exception: pass
    wav, tmpdir = to_wav(src)
    try:
        import soundfile as sf
        audio, _ = sf.read(wav, dtype='float32')
        duration = len(audio) / 16000.0
        flags = []
        if duration < 5 or float(abs(audio).max() if len(audio) else 0) < 0.01:
            return {'error': 'no usable audio', 'duration_s': round(duration, 1), 'overall_0_100': 0,
                    'speaking_cefr': 'A1', 'flags': ['no_audio'], 'version': VERSION}

        transcript, words, lang, lang_p, _ = run_whisper(audio); err(f'whisper done {time.time()-t0:.0f}s')
        lex = [w for w in words if re.sub(r"[^a-z']", '', w['w'].lower())]
        n_fill = sum(1 for w in lex if re.sub(r"[^a-z']", '', w['w'].lower()) in FILLERS)
        content = [w for w in lex if re.sub(r"[^a-z']", '', w['w'].lower()) not in FILLERS]
        nw = len(content)
        reps = sum(1 for a, b in zip(content, content[1:])
                   if re.sub(r"[^a-z']", '', a['w'].lower()) == re.sub(r"[^a-z']", '', b['w'].lower()))

        # ---- fluency ----
        if lex:
            span = max(1.0, lex[-1]['end'] - lex[0]['start'])
            gaps = [b['start'] - a['end'] for a, b in zip(lex, lex[1:])]
            pause_time = sum(g for g in gaps if g > 0.25)
            long_pauses = sum(1 for g in gaps if g > 1.5)
        else:
            span, pause_time, long_pauses = duration, duration, 0
        wpm = nw / (span / 60.0)
        pause_ratio = pause_time / span
        fill100 = 100.0 * (n_fill + reps) / max(nw, 1)
        rate_s = 100 - 1.5 * (110 - wpm) if wpm < 110 else (100 - 1.5 * (wpm - 170) if wpm > 170 else 100)
        pause_s = 100 - 200 * max(0.0, pause_ratio - 0.15)
        fill_s = 100 - 8 * max(0.0, fill100 - 2)
        fluency = clamp(0.40 * clamp(rate_s) + 0.35 * clamp(pause_s) + 0.25 * clamp(fill_s) - 5 * long_pauses)

        # ---- clarity / pronunciation ----
        w_conf = sum(w['p'] for w in content) / nw if nw else 0.0
        w2v_conf, w2v_text = run_wav2vec(audio); err(f'wav2vec2 done {time.time()-t0:.0f}s')
        ref, hyp = words_norm(transcript), words_norm(w2v_text)
        agree = max(0.0, 1.0 - wer(ref, hyp))
        clarity = clamp(0.35 * clamp((w_conf - 0.5) / 0.45 * 100) + 0.25 * clamp((w2v_conf - 0.6) / 0.38 * 100)
                        + 0.40 * clamp((agree - 0.4) / 0.5 * 100))

        # ---- accent ----
        try:
            acc_label, acc_conf, dist = run_accent(audio)
            accent_mass = clamp(100 * sum(p * NEUTRAL.get(l, 0.0) for l, p in dist.items()))
            # The accent model has no Spanish/LatAm class and is fooled by clear-but-foreign speech, so an accent only
            # counts as neutral if a native-English acoustic model also understands it: neutral = min(accent, clarity).
            neutral = min(accent_mass, clarity)
        except Exception as e:
            err('accent failed:', e); acc_label, acc_conf, dist, neutral, accent_mass = None, 0.0, {}, None, None; flags.append('accent_failed')
        err(f'accent done {time.time()-t0:.0f}s')

        # ---- grammar ----
        try:
            g_hits = run_grammar(transcript) if nw else []
            g100 = 100.0 * len(g_hits) / max(nw, 1)
            grammar = clamp(100 - GRAMMAR_PENALTY * g100)
            if agree < 0.5:                                 # transcript too garbled to trust a "clean" grammar result
                grammar = min(grammar, 50); flags.append('grammar_unreliable')
        except Exception as e:
            err('grammar failed:', e); g_hits, g100, grammar = [], None, None; flags.append('grammar_failed')
        err(f'grammar done {time.time()-t0:.0f}s')

        # ---- overall ----
        parts = [(clarity, 0.35), (fluency, 0.25), (grammar, 0.25), (neutral, 0.15)]
        parts = [(v, w) for v, w in parts if v is not None]
        overall = sum(v * w for v, w in parts) / sum(w for _, w in parts)
        if nw < 40:
            overall *= max(0.3, nw / 40.0); flags.append('too_short')
        if lang and lang != 'en' and (lang_p or 0) > 0.5:
            overall = min(overall, 25); flags.append('not_english:' + lang)
        overall = int(round(clamp(overall)))
        cefr = 'C1' if overall >= 85 else 'B2' if overall >= 75 else 'B1' if overall >= 60 else 'A2' if overall >= 45 else 'A1'
        return {
            'transcript': transcript, 'duration_s': round(duration, 1), 'words': nw, 'wpm': round(wpm),
            'pause_ratio': round(pause_ratio, 2), 'long_pauses': long_pauses, 'fillers': n_fill, 'repetitions': reps,
            'grammar_errors_per_100w': None if g100 is None else round(g100, 1),
            'grammar_examples': g_hits[:5],
            'clarity': int(round(clarity)), 'fluency': int(round(fluency)),
            'grammar': None if grammar is None else int(round(grammar)),
            'accent_label': acc_label, 'accent_conf': round(acc_conf, 2),
            'accent_top3': {k: round(v, 2) for k, v in list(dist.items())[:3]},
            'neutral_accent_score': None if neutral is None else int(round(neutral)),
            'accent_native_mass': None if accent_mass is None else int(round(accent_mass)),
            'speaking_cefr': cefr, 'overall_0_100': overall,
            'english_prob': None if lang_p is None else round(lang_p if lang == 'en' else 1 - lang_p, 2),
            'detected_language': lang, 'flags': flags,
            'detail': {'whisper_word_conf': round(w_conf, 3), 'wav2vec2_conf': round(w2v_conf, 3),
                       'asr_agreement': round(agree, 2), 'wav2vec2_text': w2v_text[:600]},
            'version': VERSION, 'models': f'faster-whisper-{WHISPER_SIZE}-int8, wav2vec2-base-960h, commonaccent-ecapa, languagetool',
            'elapsed_s': round(time.time() - t0, 1),
        }
    finally:
        subprocess.run(['rm', '-rf', tmpdir])

if __name__ == '__main__':
    if len(sys.argv) < 2: err(__doc__); sys.exit(2)
    src = sys.stdin.buffer.read() if sys.argv[1] == '-' else sys.argv[1]
    print(json.dumps(score(src), ensure_ascii=False, indent=1))
