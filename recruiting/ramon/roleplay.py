"""Voice ROLEPLAY over WhatsApp (and the web, via rp_web.py).
The bot plays a customer; the candidate answers each of 5 objections with a VOICE NOTE.
Every answer is recorded (Supabase), transcribed + speaking-scored (local models) and graded against a rebuttal rubric.
Scenario = scenarios/<TALENT_ROLEPLAY_SCENARIO>.json (default water_treatment). Add your own: same shape, regex rubric.
State per candidate: rp = {round, asked_ts, answers:[{round, path, local, sent_ts, recv_ts, status, transcript, speaking, content}], done}"""
import os, re, time, json

HERE = os.path.dirname(os.path.abspath(__file__))
SCENARIO_ID = os.environ.get('TALENT_ROLEPLAY_SCENARIO') or 'water_treatment'
try:
    import talent as _t
    SCENARIO_ID = _t.env.get('TALENT_ROLEPLAY_SCENARIO', SCENARIO_ID)
except Exception:
    pass
SCENARIO = json.load(open(os.path.join(HERE, 'scenarios', re.sub(r'[^a-z0-9_-]', '', SCENARIO_ID) + '.json')))
ROUNDS = [{'say': r['say'], 'goal': r['goal'], 'rubric': [tuple(x) for x in r['rubric']]} for r in SCENARIO['rounds']]
PERSONA = f"{SCENARIO.get('persona_emoji', '📞')} {SCENARIO.get('persona', 'Customer')}"

def grade(rnd, transcript):
    low = (transcript or "").lower()
    got, pts = [], 0
    for label, rx, p in ROUNDS[rnd]["rubric"]:
        if re.search(rx, low): got.append(label); pts += p
    asked_q = "?" in (transcript or "") or re.search(r"\b(can i|could you|may i|what|when|where|would you)\b", low)
    words = len(low.split())
    if words < 12: pts = int(pts * 0.5)           # too short to be a real answer
    return min(20, pts), got, bool(asked_q), words

def start(T, k, force=False):
    with T.State() as d:
        c = d['c'].get(k)
        if not c or (c.get('rp') and not force): return False
        c['rp'] = {'round': 0, 'asked_ts': time.time(), 'answers': [], 'started': T.now()}
    T.wa_text(k, f"🎭 *Roleplay time!* {T.BOT_NAME} from {T.COMPANY} HR. " + SCENARIO['wa_intro'])
    T.wa_text(k, f"{PERSONA} (1/{len(ROUNDS)}): \"{ROUNDS[0]['say']}\"")
    T.log(rp_start=k); return True

def on_answer(T, k, c, msg):
    """Called from on_wa for candidates with an active roleplay. Returns True if consumed."""
    rp = c.get('rp') or {}
    if rp.get('done') or rp.get('round') is None: return False
    rnd = rp['round']; now = time.time()
    if msg.get('audio') or msg.get('video'):
        media = msg.get('audio') or msg.get('video')
        data, mime = T.wa_media(media['id'])
        ext = 'ogg' if 'ogg' in (mime or '') or msg.get('audio') else 'mp4'
        path = T.sb_upload(f"recruiting/{k}/roleplay-r{rnd+1}-{int(now)}.{ext}", data, mime or 'audio/ogg')
        local = os.path.join(T.MEDIA_DIR, f"{k}-rp{rnd+1}-{int(now)}.{ext}"); os.makedirs(T.MEDIA_DIR, exist_ok=True)
        open(local, 'wb').write(data)
        ans = {'round': rnd, 'path': path, 'local': local, 'sent_ts': rp.get('asked_ts'), 'recv_ts': now, 'status': 'pending', 'voice': True}
    else:
        txt = (msg.get('text') or {}).get('body', '')
        if not txt: return False
        ans = {'round': rnd, 'transcript': txt, 'sent_ts': rp.get('asked_ts'), 'recv_ts': now, 'status': 'typed', 'voice': False}
        pts, got, q, w = grade(rnd, txt); ans.update(content=pts, hits=got, asked_q=q, words=w)
    with T.State() as d:
        r = d['c'][k]['rp']; r['answers'].append(ans); r['round'] = rnd + 1; r['asked_ts'] = now
        finished = r['round'] >= len(ROUNDS)
        if finished: r['done'] = T.now()
    if not ans['voice']:
        T.wa_text(k, "🎙️ Tip: next time answer with a *voice note* (hold the mic button) — we need to hear you.")
    if finished:
        msg_end = f"✅ That's the end of the call, great job! We're reviewing your answers now. — {T.sig()}"
        if c.get('composite') is None:
            msg_end += "\n\nLast step: the English test (15 min), open in Chrome:\n" + T.apply_link(c)
        T.wa_text(k, msg_end)
    else:
        T.wa_text(k, f"{PERSONA} ({rnd+2}/{len(ROUNDS)}): \"{ROUNDS[rnd+1]['say']}\"")
    T.log(rp_answer=k, round=rnd + 1, voice=ans['voice'], secs=int(now - (ans['sent_ts'] or now)))
    return True

def score_pending(T):
    """Cron (venv python): transcribe + speaking-score recorded answers, grade content, post the result when all 5 are in."""
    import speech_score
    with T.State() as d: ks = [k for k, c in d['c'].items() if (c.get('rp') or {}).get('answers')]
    for k in ks:
        with T.State() as d: rp = json.loads(json.dumps(d['c'][k]['rp']))
        changed = False
        for a in rp['answers']:
            if a.get('status') == 'pending' and a.get('local') and os.path.exists(a['local']):
                res = speech_score.score(a['local'])
                a['transcript'] = (res.get('transcript') or '')[:1200]; a['speaking'] = res.get('overall_0_100'); a['cefr'] = res.get('speaking_cefr')
                pts, got, q, w = grade(a['round'], a['transcript']); a.update(content=pts, hits=got, asked_q=q, words=w, status='done')
                try: os.remove(a['local'])
                except OSError: pass
                changed = True
        if changed:
            with T.State() as d: d['c'][k]['rp']['answers'] = rp['answers']
        if rp.get('done') and not rp.get('reported') and all(a.get('status') in ('done', 'typed') for a in rp['answers']):
            report(T, k, rp)
            with T.State() as d: d['c'][k]['rp']['reported'] = T.now()

def report(T, k, rp):
    with T.State() as d: c = dict(d['c'][k])
    ans = sorted(rp['answers'], key=lambda a: a['round'])
    content = sum(a.get('content') or 0 for a in ans)                      # /100
    sp = [a['speaking'] for a in ans if a.get('speaking') is not None]
    speaking = round(sum(sp) / len(sp)) if sp else None
    voice_ratio = sum(1 for a in ans if a.get('voice')) / max(1, len(ans))
    speed = [a['recv_ts'] - a['sent_ts'] for a in ans if a.get('sent_ts')]
    fast = sum(1 for s in speed if s < 180)
    total = round(0.6 * content + 0.4 * (speaking if speaking is not None else content * 0.5) - (0 if voice_ratio == 1 else 10))
    total = max(0, min(100, total))
    verdict = '🔥 STRONG — book interview' if total >= 70 else '👍 OK — interview with coaching' if total >= 55 else '⚠️ weak'
    with T.State() as d: d['c'][k].update(rp_score=total, rp_content=content, rp_speaking=speaking)
    lines = [f"🎭 *Roleplay result: {c.get('name')}* +{k}", f"*{total}/100* · {verdict}",
             f"Objection handling {content}/100 · Speaking {speaking if speaking is not None else '-'}/100 · voice {int(voice_ratio*100)}% · fast replies {fast}/5"]
    for a in ans:
        r = ROUNDS[a['round']]
        link = T.sb_sign(a['path']) if a.get('path') else ''
        lines.append(f"\n*R{a['round']+1} — {r['goal']}*  → {a.get('content',0)}/20 ✓ {', '.join(a.get('hits') or []) or 'nothing matched'}"
                     + (f" · speaking {a.get('speaking')}" if a.get('speaking') is not None else ' · TYPED')
                     + f"\n“{(a.get('transcript') or '')[:220]}”" + (f"\n🎧 {link}" if link else ''))
    lines.append(f"\n💬 https://wa.me/{k}")
    T.cliq_text('\n'.join(lines))
    T.recruit_note(c.get('recruit_id'), f"🎭 Roleplay ({SCENARIO['id']}) {total}/100 ({verdict})", '\n'.join(lines))
    T.log(rp_report=k, total=total)
