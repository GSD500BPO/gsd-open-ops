"""Optional: post candidates who PASSED to a CLIENT's Zoho Cliq channel (TALENT_CLIENT_SHARE=1).

What the client sees: an alias (first name + initial), test scores, speaking score and the consented public reel.
What the client NEVER sees: phone, email, full name, or any pay/rate figure. Candidates stay yours until you place them.

The client's Cliq is a different Zoho org, so it has its own OAuth app:
  CLIENT_CLIQ_CLIENT_ID / CLIENT_CLIQ_CLIENT_SECRET / CLIENT_CLIQ_REFRESH_TOKEN / CLIENT_CLIQ_CHANNEL
Message copy can be edited without touching code: TALENT_CLIENT_SHARE_TEMPLATE points at a plain-text file
(first line "TITLE: ...", then the body, $alias $composite $english $sales $speaking $cefr $clarity $fluency $video).
The template is parsed as data, never executed, and is rejected if it contains anything that looks like a rate."""
import json, re, string, time, urllib.request, urllib.parse, urllib.error

_tok = {'t': None, 'exp': 0}
_STOP = ('de', 'del', 'la', 'los', 'y')


def _env(T):
    return T.env


def token(T):
    if _tok['t'] and time.time() < _tok['exp']: return _tok['t']
    e = _env(T)
    d = json.load(urllib.request.urlopen('https://accounts.zoho.com/oauth/v2/token', urllib.parse.urlencode(
        {'grant_type': 'refresh_token', 'client_id': e['CLIENT_CLIQ_CLIENT_ID'], 'client_secret': e['CLIENT_CLIQ_CLIENT_SECRET'],
         'refresh_token': e['CLIENT_CLIQ_REFRESH_TOKEN']}).encode(), timeout=30))
    _tok.update(t=d['access_token'], exp=time.time() + 3000); return _tok['t']


def send(T, msg):
    ch = _env(T).get('CLIENT_CLIQ_CHANNEL', '')
    if not ch: return 'CLIENT_CLIQ_CHANNEL not set'
    req = urllib.request.Request(f'https://cliq.zoho.com/api/v2/channelsbyname/{ch}/message', method='POST', data=json.dumps(msg).encode(),
                                 headers={'Authorization': 'Zoho-oauthtoken ' + token(T), 'Content-Type': 'application/json'})
    try: urllib.request.urlopen(req, timeout=40); return True
    except urllib.error.HTTPError as e: return 'HTTP %s %s' % (e.code, e.read()[:200])


def alias(c):
    parts = [w for w in (c.get('name') or 'Agent').split() if w.lower() not in _STOP]
    return parts[0] + (f' {parts[1][0].upper()}.' if len(parts) > 1 else '')


def build(k, c, sp, T):
    v = dict(alias=alias(c), composite=c.get('composite'), english=c.get('english'), sales=c.get('sales'),
             speaking=sp.get('overall_0_100'), cefr=sp.get('speaking_cefr') or '-', clarity=sp.get('clarity'),
             fluency=sp.get('fluency'), video=T.reel_url(k) if c.get('consent') else '(reel shared after candidate consent)')
    tpl = _env(T).get('TALENT_CLIENT_SHARE_TEMPLATE', '')
    if tpl:
        try:
            lines = [l.rstrip('\n') for l in open(tpl, encoding='utf-8') if not l.startswith('#')][:40]
            title = next(l[6:].strip() for l in lines if l.startswith('TITLE:'))
            body = '\n'.join(l for l in lines if not l.startswith('TITLE:')).strip()
            t, b = (string.Template(x).safe_substitute(v) for x in (title, body))
            if body and len(t + b) < 3000 and not re.search(r'\$\s*\d|/\s*h(r|ora)\b|\bUSD\b|\$[a-z_]+', t + b, re.I):
                return {'text': b, 'card': {'title': t[:200], 'theme': 'modern-inline'}}
            T.log(client_share='template_rejected')
        except Exception as e: T.log(client_share='template_error', e=str(e)[:150])
    return {'text': '\n'.join([
        f"*{v['alias']}* · {T.ROLE_TITLE}",
        f"📝 English test: *{v['composite']}*/100 · English {v['english']}% · Sales {v['sales']}%",
        f"🗣 Speaking *{v['speaking']}*/100 ({v['cefr']}) · clarity {v['clarity']} · fluency {v['fluency']}",
        f"🎥 Video: {v['video']}",
        f"Status: {T.COMPANY} interview in progress."]),
        'card': {'title': f"✅ {v['alias']} · test {v['composite']} · speaking {v['speaking']}", 'theme': 'modern-inline'}}


def sweep(T):
    """Only candidates who PASSED (video + test) are shared, once each. No pay, no phone/email."""
    with T.State() as d: cs = {k: dict(c) for k, c in d['c'].items()}
    for k, c in cs.items():
        if 'TEST' in (c.get('name') or '').upper() or c.get('stage') != 'passed': continue
        done = set(c.get('client_shared') or [])
        if 'passed' in done: continue
        with T.State() as d:                                   # mark BEFORE sending: at most one post per candidate
            if k in d['c']: d['c'][k]['client_shared'] = sorted(done | {'passed'})
        r = send(T, build(k, c, c.get('speech') or {}, T))
        T.log(client_share=k, what='passed', ok=r is True, r=None if r is True else str(r)[:150])
