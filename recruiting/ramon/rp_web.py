"""Web roleplay: the same scenario as roleplay.py, in the browser. Served by intake_server at /talent/roleplay.
Session files: rp_web/<sid>.json. Answers: Supabase recruiting/web-roleplay/<sid>/rN.<ext>, transcribed in a background thread."""
import json, os, re, time, threading, subprocess, secrets, uuid
import talent, roleplay
HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, 'rp_web'); os.makedirs(DIR, exist_ok=True)
VENV = os.path.join(HERE, '.venv', 'bin', 'python')
LOCK = threading.Semaphore(1)            # one transcription at a time (RAM)

def _p(sid): return os.path.join(DIR, re.sub(r'[^a-zA-Z0-9_-]', '', sid) + '.json')
def load(sid):
    try: return json.load(open(_p(sid)))
    except Exception: return None
def save(s): json.dump(s, open(_p(s['sid']), 'w'))

def start(name, phone, test=False):
    sid = uuid.uuid4().hex[:16]
    s = {'sid': sid, 'name': (name or '')[:80], 'phone': re.sub(r'\D', '', phone or '')[:15], 'test': bool(test) or 'TEST' in (name or '').upper(),
         'started': time.time(), 'answers': {}, 'asked': {}}
    save(s); talent.log(rpweb_start=sid, phone=s['phone'], test=s['test'])
    return {'sid': sid, 'rounds': [r['say'] for r in roleplay.ROUNDS]}

def asked(sid, rnd):
    s = load(sid)
    if s and str(rnd) not in s['asked']: s['asked'][str(rnd)] = time.time(); save(s)

def answer(sid, rnd, data, mime):
    s = load(sid)
    if not s or not (0 <= rnd < len(roleplay.ROUNDS)) or len(data) < 1000: return {'ok': False}
    ext = 'mp4' if 'mp4' in (mime or '') else 'ogg' if 'ogg' in (mime or '') else 'webm'
    local = os.path.join(DIR, f'{sid}-r{rnd+1}.{ext}'); open(local, 'wb').write(data)
    path = f"recruiting/web-roleplay/{sid}/r{rnd+1}.{ext}"
    s['answers'][str(rnd)] = {'round': rnd, 'path': path, 'local': local, 'recv_ts': time.time(), 'sent_ts': s['asked'].get(str(rnd)),
                              'status': 'pending', 'voice': True, 'bytes': len(data)}
    save(s)
    def _up():
        try: talent.sb_upload(path, data, mime or 'audio/webm')
        except Exception as e: talent.log(err='rpweb_upload', e=str(e)[:200])
    threading.Thread(target=_up, daemon=True).start()        # never make the candidate wait on storage
    threading.Thread(target=_transcribe, args=(sid, rnd), daemon=True).start()
    return {'ok': True}

def _transcribe(sid, rnd):
    with LOCK:
        s = load(sid); a = s['answers'][str(rnd)]
        try:
            out = subprocess.run([VENV, os.path.join(HERE, 'rp_transcribe.py'), a['local']], capture_output=True, text=True, timeout=240)
            r = json.loads(out.stdout.strip().splitlines()[-1])
            pts, got, q, w = roleplay.grade(rnd, r['text'])
            a.update(transcript=r['text'][:1200], duration=r['duration'], content=pts, hits=got, asked_q=q, words=w, status='done')
        except Exception as e:
            a.update(status='error', error=str(e)[:200])
        s = load(sid); s['answers'][str(rnd)] = a; save(s)
        talent.log(rpweb_answer=sid, round=rnd + 1, status=a['status'], content=a.get('content'))

def finish(sid):
    s = load(sid)
    if not s: return {'ok': False}
    s['finished'] = time.time(); save(s)
    threading.Thread(target=_report, args=(sid,), daemon=True).start()
    return {'ok': True}

def _report(sid):
    for _ in range(90):                                   # wait up to ~6 min for transcripts
        s = load(sid)
        if all(a.get('status') in ('done', 'error') for a in s['answers'].values()): break
        time.sleep(4)
    s = load(sid); ans = [s['answers'][k] for k in sorted(s['answers'], key=int)]
    content = sum(a.get('content') or 0 for a in ans)
    answered = len(ans)
    speed = [a['recv_ts'] - a['sent_ts'] for a in ans if a.get('sent_ts')]
    avg = round(sum(speed) / len(speed)) if speed else None
    talk = sum(a.get('duration') or 0 for a in ans)
    total = max(0, min(100, content - (5 * (5 - answered))))
    verdict = '🔥 STRONG — book interview' if total >= 70 else '👍 OK — interview with coaching' if total >= 50 else '⚠️ weak'
    name = s['name'] or 'Unknown'; k = talent.norm(s['phone']) if s['phone'] else ''
    lines = [f"🎭 *Web roleplay{' (TEST)' if s['test'] else ''}: {name}*" + (f" +{k}" if k else ''),
             f"*{total}/100* · {verdict}", f"Objection handling {content}/100 · answered {answered}/5 · talk time {round(talk)}s · avg time per round {avg}s"]
    for a in ans:
        r = roleplay.ROUNDS[a['round']]
        lines.append(f"\n*R{a['round']+1} — {r['goal']}* → {a.get('content', 0)}/20 ✓ {', '.join(a.get('hits') or []) or 'nothing matched'}"
                     f" · {a.get('duration', '?')}s\n“{(a.get('transcript') or '')[:260]}”\n🎧 {talent.sb_sign(a['path']) or ''}")
    if k: lines.append(f"\n💬 https://wa.me/{k}")
    if not name.upper().startswith('AUTOTEST'): talent.cliq_text('\n'.join(lines))   # automated test runs stay out of Cliq
    s['lines'] = lines
    s['report'] = {'total': total, 'content': content, 't': time.time()}; save(s)
    if not s['test'] and k:
        with talent.State() as d:
            kk = talent.find(d, k)
            if kk: d['c'][kk].update(rp_score=total, rp_web=sid)
            c = dict(d['c'][kk]) if kk else None
        if c: talent.recruit_note(c.get('recruit_id'), f"🎭 Web roleplay {total}/100 ({verdict})", '\n'.join(lines))
    for a in ans:
        try: os.remove(a['local'])
        except OSError: pass
    talent.log(rpweb_report=sid, total=total, test=s['test'])
