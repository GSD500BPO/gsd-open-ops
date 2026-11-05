# Ramón: open-source WhatsApp recruiting bot + talent pipeline (GSD 500 BPO, MIT).
# Flow: lead (Meta lead form, click-to-WhatsApp ad or the apply page) -> WhatsApp welcome + email -> 1-min English video in
# WhatsApp -> local speaking score (speech_score.py) -> English/Sales/Typing test -> optional voice roleplay -> pass = team chat card
# + ATS "Qualified" + interview task + (with consent) public talent profile. Fail = silent, polite.
# Safety: TALENT_LIVE=0 (default) logs every outbound action instead of sending. TALENT_ALLOW limits live WhatsApp sends to the
# listed numbers while you test. Per-candidate WhatsApp daily cap, STOP handling, consent before anything goes public.
# State lives in state.json keyed by normalized phone. Configure everything in .env (see .env.example).
import json, os, re, sys, time, urllib.request, urllib.parse, urllib.error, fcntl, subprocess, threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
STATE = os.path.join(HERE, 'state.json'); LOG = os.path.join(HERE, 'events.jsonl')

def load_env(paths):
    out = {}
    for f in paths:
        if f and os.path.exists(f):
            for l in open(f):
                if '=' in l and not l.lstrip().startswith('#'):
                    k, v = l.split('=', 1); out[k.strip()] = v.strip().strip('"\'')
    return out

# .env next to this file (or TALENT_ENV_FILE), then real environment variables win.
env = load_env([os.environ.get('TALENT_ENV_FILE') or os.path.join(HERE, '.env')])
env.update({k: v for k, v in os.environ.items() if k.startswith(('TALENT_', 'WA_', 'META_', 'ZOHO_', 'SUPABASE_', 'CLIQ_', 'CLIENT_', 'LT_', 'OUTBOUND_'))})
for _k in ('TALENT_WHISPER', 'TALENT_SPEECH_THREADS', 'TALENT_MODELS', 'LT_SERVER', 'OUTBOUND_GUARD_DIR', 'OUTBOUND_GUARD_DAILY_CAP'):
    if _k in env: os.environ.setdefault(_k, env[_k])          # read by speech_score / rp_transcribe / outbound_guard

# ---- Branding / copy (what candidates see) ----
COMPANY = env.get('TALENT_COMPANY', 'Your Company')
BOT_NAME = env.get('TALENT_BOT_NAME', 'Ramón')                     # the recruiter persona that signs WhatsApp messages
ROLE_TITLE = env.get('TALENT_ROLE_TITLE', 'SDR / BDR (English)')
PAY_LINE = env.get('TALENT_PAY_LINE', '')                         # e.g. "base pay + daily and weekly prizes"; empty = not mentioned
CAMPAIGN_BLURB = env.get('TALENT_CAMPAIGN_BLURB', 'inbound and outbound calls with U.S. customers')
WA_DISPLAY = env.get('TALENT_WA_DISPLAY', '')                     # human-readable WhatsApp number shown in emails
WA_LINK = env.get('TALENT_WA_LINK', '')                           # https://wa.me/<digits>
TALENT_SITE = env.get('TALENT_SITE_URL', '')                      # public talent page, shown in the consent message

# ---- Jobs / sources ----
FORM_ID = env.get('TALENT_FORM_ID', '')                           # Meta lead form id (optional)
JOB_ID = env.get('TALENT_JOB_ID', '')                             # Zoho Recruit job opening id
# Reusable for any opening: jobs.json = [{"form_id": "...", "job_id": "<Recruit job id>", "title": "..."}]
_jobs_f = os.path.join(HERE, 'jobs.json')
JOBS = json.load(open(_jobs_f)) if os.path.exists(_jobs_f) else ([{'form_id': FORM_ID, 'job_id': JOB_ID, 'title': ROLE_TITLE}] if FORM_ID else [])
CLIQ_CHANNEL = env.get('TALENT_CLIQ_CHANNEL', 'recruiting')       # Zoho Cliq channel unique name for the team
APPLY_URL = env.get('TALENT_APPLY_URL', 'https://example.com/talent/apply')
MAIL_FROM = env.get('TALENT_MAIL_FROM', '')
MAIL_CC = env.get('TALENT_MAIL_CC', '')                           # recruiting team copy
HIRING_INBOX = env.get('TALENT_HIRING_INBOX', MAIL_FROM)
PASS_COMPOSITE = int(env.get('TALENT_PASS_COMPOSITE', '65')); PASS_ENGLISH = int(env.get('TALENT_PASS_ENGLISH', '70'))
LIVE = env.get('TALENT_LIVE', '0') == '1'
ALLOW = {re.sub(r'\D', '', x) for x in env.get('TALENT_ALLOW', '').split(',') if x.strip()}
WA_PH = env.get('WA_PHONE_NUMBER_ID', ''); WA_T = env.get('WA_ACCESS_TOKEN', ''); G = 'https://graph.facebook.com/v21.0/'
WA_LANG = env.get('TALENT_WA_TEMPLATE_LANG', 'en')
TPL_STEPS = env.get('TALENT_WA_TEMPLATE_STEPS', 'recruiting_steps_en')          # approved template: {{1}} first name, {{2}} test link
TPL_WELCOME = env.get('TALENT_WA_TEMPLATE_WELCOME', 'recruiting_welcome_en')    # fallback: {{1}} first name
TPL_REMINDER = env.get('TALENT_WA_TEMPLATE_REMINDER', 'recruiting_reminder_en') # {{1}} first name
SB = env.get('SUPABASE_URL', ''); SBK = env.get('SUPABASE_SERVICE_KEY', '')
VIDEO_BUCKET = env.get('TALENT_VIDEO_BUCKET', 'agent-videos')     # PRIVATE bucket; reviewers get signed links
REELS = env.get('TALENT_REELS_BUCKET', 'talent-video-reels')      # PUBLIC bucket the website plays consented reels from
PHOTOS = env.get('TALENT_PHOTOS_BUCKET', 'agent-photos')          # PUBLIC bucket for profile stills
REEL_SALT = env.get('TALENT_REEL_SALT', '')                       # REQUIRED for publishing: random secret so public URLs can't be derived from phones
MARKETPLACE_CATEGORY = env.get('TALENT_MARKETPLACE_CATEGORY', '') or None
DEFAULT_CC = env.get('TALENT_DEFAULT_COUNTRY_CODE', '')           # e.g. 57: a bare 10-digit local mobile gets this prefix
LOCAL_MOBILE_PREFIX = env.get('TALENT_LOCAL_MOBILE_PREFIX', '3')
# Speaking score (speech_score.py, local models in .venv). Runs in a detached background process after a video lands.
PASS_SPEAKING = int(env.get('TALENT_PASS_SPEAKING', '60'))          # overall_0_100 needed to pass
SPEECH_ON = env.get('TALENT_SPEECH', '1') == '1'
SPEECH_ON_ERROR = env.get('TALENT_SPEECH_ON_ERROR', 'review')       # review = card flagged "not scored"; fail = drop
SPEECH_TIMEOUT = int(env.get('TALENT_SPEECH_TIMEOUT', '1500'))      # seconds (includes waiting for the one-at-a-time lock)
VENV_PY = env.get('TALENT_VENV_PYTHON', os.path.join(HERE, '.venv', 'bin', 'python'))
MEDIA_DIR = os.path.join(HERE, 'media')                             # local copy for scoring; deleted after scoring when LIVE
SPEECH_LOG = env.get('TALENT_SPEECH_LOG', os.path.join(HERE, 'logs', 'talent-speech.log'))

def now(): return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
def log(**k):
    k['t'] = now(); open(LOG, 'a').write(json.dumps(k, ensure_ascii=False) + '\n')

def first_name(c): return (c.get('name') or 'there').split(' ')[0] or 'there'
def sig(): return f"{BOT_NAME}, {COMPANY} HR"

def norm(p):
    d = re.sub(r'\D', '', p or '')
    if DEFAULT_CC and len(d) == 10 and d.startswith(LOCAL_MOBILE_PREFIX): d = DEFAULT_CC + d   # local mobile without country code
    return d

class State:
    def __enter__(self):
        self.fh = open(STATE + '.lock', 'w'); fcntl.flock(self.fh, fcntl.LOCK_EX)
        self.d = json.load(open(STATE)) if os.path.exists(STATE) else {'c': {}, 'meta_since': 0, 'bucket_seen': []}
        return self.d
    def __exit__(self, *a):
        tmp = STATE + '.tmp'; json.dump(self.d, open(tmp, 'w'), ensure_ascii=False, indent=1); os.replace(tmp, STATE)
        fcntl.flock(self.fh, fcntl.LOCK_UN); self.fh.close()

def find(d, phone=None, email=None):
    k = norm(phone)
    if k and k in d['c']: return k
    if k:
        for kk in d['c']:
            if kk[-10:] == k[-10:]: return kk
    e = (email or '').strip().lower()
    if e:
        for kk, c in d['c'].items():
            if c.get('email', '').lower() == e: return kk
    return None

def may_send(phone):
    if not LIVE: return False
    return not ALLOW or norm(phone) in ALLOW

# ---------- HTTP ----------
def http(method, url, data=None, headers=None, raw=False, timeout=60):
    h = dict(headers or {})
    if isinstance(data, (dict, list)): data = json.dumps(data).encode(); h.setdefault('Content-Type', 'application/json')
    r = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            b = resp.read(); return (b, resp.headers.get('Content-Type')) if raw else (json.loads(b) if b.strip() else {})
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf8', 'replace')[:500]
        if raw: raise RuntimeError(f'{e.code} {body}')
        return {'_err': e.code, '_body': body}

_tok = {}
def zoho_token(kind):
    if kind in _tok and _tok[kind][1] > time.time(): return _tok[kind][0]
    if kind == 'recruit': cid, sec, ref = env['ZOHO_CLIENT_ID'], env['ZOHO_CLIENT_SECRET'], env['ZOHO_RECRUIT_REFRESH_TOKEN']
    else: cid, sec, ref = env['ZOHO_MAIL_CLIENT_ID'], env['ZOHO_MAIL_CLIENT_SECRET'], env['ZOHO_MAIL_REFRESH_TOKEN']
    q = urllib.parse.urlencode({'grant_type': 'refresh_token', 'client_id': cid, 'client_secret': sec, 'refresh_token': ref}).encode()
    r = http('POST', 'https://accounts.zoho.com/oauth/v2/token', q, {'Content-Type': 'application/x-www-form-urlencoded'})
    _tok[kind] = (r['access_token'], time.time() + 3000); return r['access_token']

# ---------- WhatsApp ----------
WA_DAILY_CAP = int(env.get('TALENT_WA_DAILY_CAP', '4'))   # hard cap on automated WhatsApp messages per candidate per day
def wa(to, payload, what):
    if not may_send(to): log(dry='wa', to=to, what=what); return {'dry': True}
    kk = norm(to); today = time.strftime('%Y-%m-%d')
    with State() as d:
        cc = d['c'].get(kk) or {}
        if cc.get('quiet') or cc.get('stage') == 'stopped':
            log(blocked='quiet', to=kk, what=what); return {'_err': 'quiet'}
        cnt = cc.get('wa_count') or {}
        if cnt.get(today, 0) >= WA_DAILY_CAP:
            log(blocked='daily_cap', to=kk, what=what); return {'_err': 'cap'}
        if kk in d['c']: d['c'][kk]['wa_count'] = {today: cnt.get(today, 0) + 1}
    body = {'messaging_product': 'whatsapp', 'to': norm(to), **payload}
    r = http('POST', G + WA_PH + '/messages', body, {'Authorization': 'Bearer ' + WA_T})
    log(sent='wa', to=to, what=what, ok='messages' in r, r=str(r)[:200]); return r

def wa_template(to, name, params):
    comps = [{'type': 'body', 'parameters': [{'type': 'text', 'text': str(p)} for p in params]}] if params else []
    return wa(to, {'type': 'template', 'template': {'name': name, 'language': {'code': WA_LANG}, 'components': comps}}, name)

def wa_text(to, text): return wa(to, {'type': 'text', 'text': {'body': text}}, 'text:' + text[:40])

def wa_media(media_id):
    meta = http('GET', G + media_id, headers={'Authorization': 'Bearer ' + WA_T})
    b, ct = http('GET', meta['url'], headers={'Authorization': 'Bearer ' + WA_T}, raw=True, timeout=180)
    return b, meta.get('mime_type') or ct

# ---------- Email (Zoho Mail API) ----------
def email(to, subject, html, what):
    if not to: return
    if not may_send_email(to): log(dry='email', to=to, what=what); return
    import outbound_guard as og                                         # per-recipient daily cap + kill switch (see outbound_guard.py)
    dom = MAIL_FROM.split('@')[-1].lower() if '@' in MAIL_FROM else None
    internal = bool(dom) and to.strip().lower().endswith('@' + dom)     # team inbox (e.g. hire alerts) gets a higher cap
    if not og.allow(to, 'email', 'talent', cap=50 if internal else None, note=what):
        log(blocked='outbound_guard', to=to, what=what); return
    r = http('POST', f"https://mail.zoho.com/api/accounts/{env['ZOHO_MAIL_ACCOUNT_ID']}/messages",
             {'fromAddress': MAIL_FROM, 'toAddress': to, 'subject': subject, 'content': html, 'mailFormat': 'html',
              **({'ccAddress': MAIL_CC} if MAIL_CC else {})},
             {'Authorization': 'Zoho-oauthtoken ' + zoho_token('mail')})
    log(sent='email', to=to, what=what, ok=r.get('status', {}).get('code') == 200, r=str(r)[:200])

EMAIL_ALLOW = {x.strip().lower() for x in env.get('TALENT_EMAIL_ALLOW', '').split(',') if x.strip()}
def may_send_email(addr):
    if not LIVE: return False
    return not (ALLOW or EMAIL_ALLOW) or addr.lower() in EMAIL_ALLOW

def apply_link(c):
    q = {'src': 'wa', 'p': '+' + c['phone']}
    if c.get('email'): q['e'] = c['email']
    return APPLY_URL + '?' + urllib.parse.urlencode(q)

# ---------- Zoho Recruit ----------
RB = 'https://recruit.zoho.com/recruit/v2/'
def recruit(method, path, body=None):
    if not LIVE and method != 'GET': log(dry='recruit', path=path, body=str(body)[:300]); return {'dry': True}
    return http(method, RB + path, body, {'Authorization': 'Zoho-oauthtoken ' + zoho_token('recruit')})

def recruit_upsert(c):
    found = http('GET', RB + 'Candidates/search?' + urllib.parse.urlencode({'phone': '+' + c['phone']}),
                 headers={'Authorization': 'Zoho-oauthtoken ' + zoho_token('recruit')})
    if isinstance(found, dict) and found.get('data'): return found['data'][0]['id']
    first, _, last = (c.get('name') or 'Candidate').strip().partition(' ')
    rec = {'First_Name': first, 'Last_Name': last or first, 'Email': c.get('email') or None, 'Mobile': '+' + c['phone'],
           'Source': 'Facebook' if c['source'] == 'meta' else 'CareerSite', 'Candidate_Status': 'New',
           'Additional_Info': c.get('form_summary', '')}
    r = recruit('POST', 'Candidates', {'data': [rec], 'trigger': []}); log(recruit_create=str(r)[:300])
    rid = (r.get('data') or [{}])[0].get('details', {}).get('id') if not r.get('dry') else None   # DUPLICATE_DATA also returns the existing id
    if rid: recruit('PUT', 'Candidates/actions/associate', {'data': [{'ids': [rid], 'jobids': [c.get('job_id') or JOB_ID], 'comments': 'Applied: ' + c.get('job_title', ROLE_TITLE)}]})
    return rid

def recruit_note(rid, title, content):
    if rid: recruit('POST', 'Notes', {'data': [{'Note_Title': title, 'Note_Content': content, 'Parent_Id': rid, 'se_module': 'Candidates'}]})

def recruit_status(rid, status):
    if rid: recruit('PUT', 'Candidates', {'data': [{'id': rid, 'Candidate_Status': status}], 'trigger': []})

# ---------- Supabase ----------
def sb_upload(path, data, mime):
    if not LIVE: log(dry='upload', path=path, bytes=len(data)); return path
    h = {'apikey': SBK, 'Authorization': 'Bearer ' + SBK, 'Content-Type': mime or 'video/mp4', 'x-upsert': 'true'}
    r = http('POST', f'{SB}/storage/v1/object/{VIDEO_BUCKET}/{path}', data, h, timeout=300)
    log(upload=path, r=str(r)[:200]); return path

def sb_sign(path, days=7):
    r = http('POST', f'{SB}/storage/v1/object/sign/{VIDEO_BUCKET}/{path}', {'expiresIn': days * 86400},
             {'apikey': SBK, 'Authorization': 'Bearer ' + SBK})
    return SB + '/storage/v1' + r['signedURL'] if r.get('signedURL') else None

REELS = 'talent-video-reels'   # public bucket the website plays from
def reel_key(k):
    import hashlib
    if not REEL_SALT: raise RuntimeError('TALENT_REEL_SALT is not set: refusing to build a public URL from a phone number')
    return hashlib.sha256((REEL_SALT + ':' + k).encode()).hexdigest()[:20]

def reel_url(k): return f'{SB}/storage/v1/object/public/{REELS}/talent/{reel_key(k)}.mp4'

# Optional public card rate by score: TALENT_RATE_LADDER="90:R1,80:R2,0:R3" (min score:hourly rate). Empty = no rate shown.
RATE_LADDER = sorted(((int(a), float(b)) for a, b in (x.split(':') for x in env.get('TALENT_RATE_LADDER', '').split(',') if ':' in x)), reverse=True)
def rate_for(c):
    """Card rate from the score shown on the card (test composite, else video speaking). None when no ladder is configured."""
    if not RATE_LADDER: return None
    sc = c.get('composite')
    if sc is None: sc = (c.get('speech') or {}).get('overall_0_100') or 0
    return next((r for mn, r in RATE_LADDER if sc >= mn), None)

def recruit_tags(c):
    rid = c.get('recruit_id')
    if not rid: return
    sp = (c.get('speech') or {}).get('overall_0_100')
    t = []
    if sp is not None: t.append('Speaking 80+' if sp >= 80 else 'Speaking 60-79' if sp >= 60 else 'Speaking under 60')
    if c.get('composite') is not None:
        t.append('Test passed' if c.get('stage') == 'passed' or ((c['composite'] or 0) >= PASS_COMPOSITE and (c.get('english') or 0) >= PASS_ENGLISH) else 'Test failed')
    if c.get('mp_id'): t.append('On website')
    if rate_for(c) is not None: t.append(f'Rate {rate_for(c)}')
    try: log(tags=c['phone'], r=str(recruit('POST', 'Candidates/actions/add_tags?' + urllib.parse.urlencode({'ids': rid, 'tag_names': ','.join(t)}), None))[:160])
    except Exception as e: log(err='tags', e=str(e)[:200])

def profile_photo(c):
    """Frame from the candidate's own video -> public agent-photos/talent/<reel_key>.jpg (same as the hand-loaded cards)."""
    try:
        url = sb_sign(c['video_path'], 1)
        out = f"/tmp/{reel_key(c['phone'])}.jpg"
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', '3', '-i', url, '-frames:v', '1', '-vf', 'scale=480:-2', out], timeout=120, check=True)
        h = {'apikey': SBK, 'Authorization': 'Bearer ' + SBK, 'Content-Type': 'image/jpeg', 'x-upsert': 'true'}
        key = f"talent/{reel_key(c['phone'])}.jpg"
        http('POST', f'{SB}/storage/v1/object/{PHOTOS}/{key}', open(out, 'rb').read(), h)
        os.remove(out)
        return f'{SB}/storage/v1/object/public/{PHOTOS}/{key}'
    except Exception as e:
        log(err='photo', k=c.get('phone'), e=str(e)[:200]); return None

CV_KW = {
    'call center': r'call ?cent(er|re)|contact cent(er|re)|bpo',
    'inbound': r'inbound', 'outbound': r'outbound|cold call',
    'appointment setting': r'appointment|schedul(e|ing) (meetings|appointments)|setter',
    'sales': r'\bsales?\b|closing|quota', 'customer service': r'customer (service|support|care)',
    'US clients/accounts': r'\bU\.?S\.?A?\b|united states|american', 'CRM': r'crm|salesforce|hubspot|zoho|five9|vicidial|mojo',
    'leadership': r'supervisor|team lead|manager|coach', 'big BPO': r'foundever|teleperformance|concentrix|sitel|ttec|alorica|atento|konecta|startek|transcom',
    'home services': r'insurance|claims|roof|restoration|hvac|solar|water treatment|home service'}
def cv_analyze(c, data):
    """Local CV read (no paid API): text -> flags + years; Recruit note + stored summary for the Cliq card."""
    try:
        f = f"/tmp/cv-{c['phone']}"; open(f, 'wb').write(data)
        t = subprocess.run(['pdftotext', '-layout', f, '-'], capture_output=True, text=True, timeout=60).stdout
        os.remove(f)
        if len(t.strip()) < 80: return None
        low = t.lower()
        hits = [k for k, rx in CV_KW.items() if re.search(rx, low)]
        yrs = sorted({int(y) for y in re.findall(r'\b(20[0-2][0-9]|19[89][0-9])\b', t)})
        span = (max(yrs) - min(yrs)) if len(yrs) > 1 else None
        langs = [l for l in ('english', 'spanish', 'portuguese', 'french', 'german', 'italian') if l in low]
        score = min(100, 10 * len(hits) + (10 if span and span >= 3 else 0))
        summ = (f"CV fit {score}/100 · " + (', '.join(hits) or 'no call-center keywords') +
                (f" · work history ~{span} yrs" if span else '') + (f" · languages: {', '.join(langs)}" if langs else ''))
        with State() as d: d['c'][c['phone']]['cv_summary'] = summ
        recruit_note(c.get('recruit_id'), '📄 CV analysis (auto)', summ + '\n\n' + ' '.join(t.split())[:1500])
        log(cv_analysis=c['phone'], summary=summ[:200]); return summ
    except Exception as e:
        log(err='cv_analyze', k=c.get('phone'), e=str(e)[:200]); return None

ASKRE = re.compile(r'\?|\b(next|link|email|e-mail|correo|video|work(ing)?|funciona|abre|open|how|what|when|where|cuando|cómo|como|qué|que sigue|siguiente|help|ayuda|test|prueba|interview|entrevista|pay|salary|pago|schedule|horario)\b', re.I)
def next_step_reply(c):
    """The bot answers 'what's next / link doesn't work / email?' with the candidate's exact next step."""
    first = first_name(c); st = c.get('stage'); has_video = bool(c.get('video_path') or c.get('video_url'))
    link = apply_link(c)
    fix = ("If the link doesn't open, copy it into Chrome. Fill in your email there (any email you use), answer the 3 short modules "
           "(English, Sales, Typing) and press *Submit application*. No CV needed.")
    if st == 'passed':
        body = "You already passed ✅ Our team will contact you here to schedule your interview. Please keep your phone close."
    elif st == 'failed':
        body = "Thank you for taking the test. Your results don't fit this role right now, but we keep your profile for upcoming roles."
    elif has_video and c.get('composite') is None:
        body = f"Your video is in ✅ — no more videos needed. Next step: the English test (about 15 min):\n{link}\n\n{fix}"
    elif c.get('composite') is not None and not has_video:
        body = "Your test is in ✅. Last step: send your 1-minute video IN ENGLISH right here in this chat."
    else:
        body = ("Next step: record a 1-minute video IN ENGLISH with your phone and send it right here in this chat "
                "(who you are, your call center experience, why you perform under pressure). No email needed for this step.\n\n"
                f"Then take the English test:\n{link}\n{fix}")
    return f"Hi {first}! {BOT_NAME} from {COMPANY} HR 🙂 " + body

HIRING_OPEN = env.get('TALENT_HIRING_OPEN', '1') == '1'
CONSENT_RE = re.compile(r'^\s*(yes|yes!|si|sí|ok|okay|claro|acepto|de acuerdo|i agree|agree|dale|listo)\b', re.I)
def ask_consent(c):
    """Data-protection consent (e.g. Colombia Ley 1581 / GDPR-style): ask before showing anyone on a public page."""
    if c.get('consent') or c.get('consent_asked'): return
    first = first_name(c)
    intro = ("" if HIRING_OPEN else "This hiring round is closed for now, but we'll be hiring more people soon. ")
    r = wa_text(c['phone'], f"{first}, {BOT_NAME} from {COMPANY} HR here 🙂 {intro}"
                f"May we show your profile on our talent site{(' (' + TALENT_SITE + ')') if TALENT_SITE else ''} so companies can hire you? "
                "We show only your first name + initial, your intro video and your scores — never your phone or email.\n\n"
                "Reply *YES* to agree (you can ask us to remove it anytime).")
    with State() as d: d['c'][c['phone']]['consent_asked'] = now()
    log(consent_asked=c['phone'], ok=not (r or {}).get('_err'))

def publish_video(c):
    """Every scored video goes to the website marketplace as PENDING (admin approves at /admin/talent-review), priced by score."""
    if not LIVE or not c.get('video_path'): return None
    if not c.get('consent') and not c.get('mp_id'):
        ask_consent(c); return None
    k = c['phone']; dest = f"talent/{reel_key(k)}.mp4"          # never put the phone number in a public URL
    h = {'apikey': SBK, 'Authorization': 'Bearer ' + SBK}
    r = http('POST', f'{SB}/storage/v1/object/copy', {'bucketId': VIDEO_BUCKET, 'sourceKey': c['video_path'], 'destinationBucket': REELS, 'destinationKey': dest}, h)
    if 'already exists' in str(r).lower() or 'Duplicate' in str(r):
        r = {'ok': 'exists'}
    log(reel_copy=k, r=str(r)[:160])
    url = reel_url(k)
    sp = c.get('speech') or {}
    parts = [w for w in (c.get('name') or 'Agent').split() if w.lower() not in ('de', 'del', 'la', 'los', 'y', 'jesus', 'jesús')]
    disp = parts[0] + (f' {parts[1][0].upper()}.' if len(parts) > 1 else '')
    row = {'display_name': disp, 'title': ROLE_TITLE, 'video_url': url, 'hourly_rate': rate_for(c),
           'bio': f"Video speaking score {sp.get('overall_0_100')}/100 {sp.get('speaking_cefr') or ''}.".strip(),
           'languages': ['English', 'Spanish'], 'skills': ['Inbound calls', 'Appointment setting'],
           'vetting_tier': 2 if (sp.get('overall_0_100') or 0) >= 80 else 1,
           'category_id': MARKETPLACE_CATEGORY, 'last_qualified_at': (c.get('speech_at') or c.get('video_at') or now())}
    ph = profile_photo(c)
    if ph: row['photo_url'] = ph
    for f, v in (('english_score', c.get('english')), ('sales_score', c.get('sales')), ('typing_wpm', c.get('wpm')), ('composite_score', c.get('composite'))):
        if v is not None: row[f] = v
    hh = dict(h, Prefer='return=representation')
    if c.get('mp_id'):
        row.pop('display_name', None)                  # keep names edited by hand on the site
        r = http('PATCH', f"{SB}/rest/v1/talent_profiles?id=eq.{c['mp_id']}", row, hh)
    else:
        # consented candidates go up as approved; everyone else stays pending (admin-only) until they say YES
        row.update(status='approved' if c.get('consent') else 'pending',
                   available_now=True, email=c.get('email') or None)
        r = http('POST', f'{SB}/rest/v1/talent_profiles', row, hh)
        if isinstance(r, list) and r:
            with State() as d: d['c'][k]['mp_id'] = r[0]['id']
            c['mp_id'] = r[0]['id']
    log(marketplace=k, r=str(r)[:160])
    return c.get('mp_id')

def marketplace_pending(c):
    if c.get('mp_id') or c.get('video_path'):          # already on the site (or can be): update instead of duplicating
        publish_video(c); recruit_tags(c); return
    # Pending = only admins see it (RLS: public sees status='approved'). Approve from /admin/talent-review.
    row = {'display_name': c.get('name'), 'email': c.get('email'), 'title': ROLE_TITLE, 'video_url': c.get('video_url'),
           'english_score': c.get('english'), 'sales_score': c.get('sales'), 'typing_wpm': c.get('wpm'),
           'composite_score': c.get('composite'), 'status': 'pending', 'hourly_rate': rate_for(c),
           'languages': ['English', 'Spanish'], 'skills': ['Inbound calls', 'Appointment setting']}
    if not LIVE: log(dry='marketplace', row=row); return
    r = http('POST', f'{SB}/rest/v1/talent_profiles', row, {'apikey': SBK, 'Authorization': 'Bearer ' + SBK, 'Prefer': 'return=representation'})
    log(marketplace=str(r)[:200])

# ---------- Cliq ----------
def cliq_card(c):
    lines = [f"*{c.get('name')}*  ·  +{c['phone']}  ·  {c.get('email') or 'no email'}",
             f"English {c.get('english')}% · Sales {c.get('sales')}% · Typing {c.get('wpm')} WPM · Composite *{c.get('composite')}*/100",
             speech_line(c),
             f"Form: {c.get('form_summary', '-')}",
             f"🎥 Video: {sb_sign(c['video_path']) if c.get('video_path') and LIVE else c.get('video_url') or '-'}",
             f"💬 WhatsApp: https://wa.me/{c['phone']}",
             f"📋 Recruit: https://recruit.zoho.com/recruit/org/Candidates/{c.get('recruit_id')}" if c.get('recruit_id') else '']
    msg = {'text': '\n'.join(l for l in lines if l),
           'card': {'title': '✅ Passed: video + English test + speaking. Book the interview' if c.get('speech_status') == 'done'
                    else '⚠️ Passed English test. Speaking NOT auto-scored: watch the video first', 'theme': 'modern-inline'}}
    if not LIVE: log(dry='cliq', msg=msg); return
    import cliq
    r = cliq.post(CLIQ_CHANNEL, msg); log(cliq=str(r)[:200])

# ---------- Speaking score ----------
INTERVIEWER = env.get('TALENT_INTERVIEWER_ID', '')   # Zoho Recruit user id of the recruiter who books interviews
def interview_task(c):
    """Passed -> Recruit Task for your own interview before any client sees the candidate."""
    rid = c.get('recruit_id')
    if not rid: return
    sp = (c.get('speech') or {}).get('overall_0_100')
    if not INTERVIEWER: log(skip='interview_task', why='TALENT_INTERVIEWER_ID not set'); return
    body = {'data': [{'Subject': f"Interview: {c.get('name')} ({ROLE_TITLE})", 'Owner': {'id': INTERVIEWER},
                      'Due_Date': time.strftime('%Y-%m-%d'), 'Priority': 'High', 'Status': 'Not Started',
                      '$se_module': 'Candidates', 'What_Id': rid,
                      'Description': f"Passed: test {c.get('composite')} · English {c.get('english')} · speaking {sp}. "
                                     f"WhatsApp https://wa.me/{c['phone']} — book the interview, then present to the client."}]}
    try: log(interview_task=c['phone'], r=str(recruit('POST', 'Tasks', body))[:200])
    except Exception as e: log(err='interview_task', e=str(e)[:200])

def cliq_text(txt):
    if not LIVE: log(dry='cliq', msg=txt); return
    try:
        import cliq
        cliq.post(CLIQ_CHANNEL, {'text': txt})
    except Exception as e: log(err='cliq_text', e=str(e)[:200])

STAGE_LABEL = {'welcomed': 'waiting on video', 'reminded': 'waiting on video', 'video_in': 'video in, waiting on test',
            'test_passed_no_video': 'test passed, missing video', 'passed': '✅ PASSED, interview', 'failed': '❌ did not pass',
            'screened_out_english': 'basic English (screened out)', 'stopped': 'STOP'}
def card_lines(c):
    """Full candidate card for the INTERNAL recruiting channel (phone, email, scores). Never send this to a client."""
    s = c.get('speech') or {}
    test = (f"📝 Test: composite *{c.get('composite')}* · English {c.get('english')}% · Sales {c.get('sales')}% · Typing {c.get('wpm')} WPM"
            if c.get('composite') is not None else '📝 Test: not taken yet')
    return [f"*{c.get('name')}*",
            f"📞 +{c['phone']}  ·  ✉️ {c.get('email') or 'no email'}  ·  source {c.get('source') or '-'}",
            f"📍 Stage: {STAGE_LABEL.get(c.get('stage'), c.get('stage'))}" + (f"  ·  rate ${rate_for(c)}/hr" if rate_for(c) is not None else ''),
            speech_line(c) if s or c.get('video_path') else '🗣 Speaking: no video yet',
            test,
            f"📋 Form: {c.get('form_summary')}" if c.get('form_summary') else '',
            f"🎥 Video: {sb_sign(c['video_path']) if c.get('video_path') and LIVE else c.get('video_url') or '-'}" if (c.get('video_path') or c.get('video_url')) else '',
            f"📄 CV: {sb_sign(c['resume_path']) if c.get('resume_path') and LIVE else c.get('resume_url')}" if (c.get('resume_path') or c.get('resume_url')) else '',
            f"🧾 {c.get('cv_summary')}" if c.get('cv_summary') else '',
            f"💬 WhatsApp: https://wa.me/{c['phone']}",
            f"📋 Recruit: https://recruit.zoho.com/recruit/org/Candidates/{c.get('recruit_id')}" if c.get('recruit_id') else '']

def cliq_card_post(c, title, channel=None):
    msg = {'text': '\n'.join(l for l in card_lines(c) if l), 'card': {'title': title, 'theme': 'modern-inline'}}
    if not LIVE: log(dry='cliq', msg=msg); return
    try:
        import cliq
        r = cliq.post(channel or CLIQ_CHANNEL, msg); log(cliq_card=c['phone'], title=title[:40], r=str(r)[:80])
    except Exception as e: log(err='cliq_card', e=str(e)[:200])

def cliq_video(c):
    """One internal post per scored video, before the English test."""
    s = c.get('speech') or {}
    tr = (s.get('transcript') or '').strip()
    lines = [f"*{c.get('name')}*  ·  +{c['phone']}  ·  {c.get('source') or '-'}",
             speech_line(c),
             f"📝 \"{tr[:280]}{'…' if len(tr) > 280 else ''}\"" if tr else '',
             f"🎥 Video: {sb_sign(c['video_path']) if c.get('video_path') and LIVE else c.get('video_url') or '-'}",
             f"💬 WhatsApp: https://wa.me/{c['phone']}",
             f"📋 Recruit: https://recruit.zoho.com/recruit/org/Candidates/{c.get('recruit_id')}" if c.get('recruit_id') else '',
             'Next: English test link already sent on WhatsApp.' if c.get('composite') is None else f"English test: composite {c.get('composite')}/100"]
    sc = s.get('overall_0_100')
    title = (f"🎥 New video · {sc}/100 {s.get('speaking_cefr') or ''}" if sc is not None else '🎥 New video · not auto-scored, watch it')
    cliq_card_post(c, title)

def speech_line(c):
    s = c.get('speech') or {}
    if c.get('speech_status') != 'done' or s.get('overall_0_100') is None:
        return f"🗣 Speaking: NOT scored ({c.get('speech_status') or 'no video file'}). Watch the video before booking"
    g = s.get('grammar_errors_per_100w')
    return (f"🗣 Speaking *{s.get('overall_0_100')}*/100 ({s.get('speaking_cefr')}) · Clarity {s.get('clarity')} · "
            f"Fluency {s.get('fluency')} ({s.get('wpm')} wpm, pauses {int(round(100 * (s.get('pause_ratio') or 0)))}%, "
            f"{s.get('fillers')} fillers) · Grammar {s.get('grammar')} ({'-' if g is None else g} err/100w) · "
            f"Accent {s.get('accent_label')} {int(round(100 * (s.get('accent_conf') or 0)))}% · neutral {s.get('neutral_accent_score')}"
            + (f" · flags {','.join(s['flags'])}" if s.get('flags') else ''))

def recruit_attach(rid, data, filename, mime='video/mp4', category='Others'):
    """Attach a file (the intro video) to the Recruit candidate so it plays inside Recruit."""
    if not rid: return None
    if not LIVE: log(dry='recruit_attach', rid=rid, name=filename, bytes=len(data)); return {'dry': True}
    b = '----gsdtalent' + str(int(time.time()))
    body = (f'--{b}\r\nContent-Disposition: form-data; name="attachments_category"\r\n\r\n{category}\r\n'
            f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n').encode() \
           + data + f'\r\n--{b}--\r\n'.encode()
    req = urllib.request.Request(f'{RB}Candidates/{rid}/Attachments', data=body, method='POST',
                                 headers={'Authorization': 'Zoho-oauthtoken ' + zoho_token('recruit'),
                                          'Content-Type': f'multipart/form-data; boundary={b}'})
    try: r = json.load(urllib.request.urlopen(req, timeout=300))
    except urllib.error.HTTPError as e: r = {'_err': e.code, 'body': e.read().decode()[:300]}
    log(recruit_attach=rid, name=filename, r=str(r)[:200]); return r

def speech_card(s):
    """Readable note for the ATS: score card + transcript."""
    if s.get('error'): return f"Speaking NOT auto-scored ({s['error']}). Watch the video before booking."
    acc = s.get('accent_label') or '-'
    lines = [f"Speaking {s.get('overall_0_100')}/100 ({s.get('speaking_cefr')}) · pass mark {PASS_SPEAKING}",
             f"Clarity {s.get('clarity')} · Fluency {s.get('fluency')} ({s.get('wpm')} wpm, pauses {round((s.get('pause_ratio') or 0) * 100)}%, {s.get('fillers')} fillers)",
             f"Grammar {s.get('grammar')} ({s.get('grammar_errors_per_100w')} errors/100 words) · Accent {acc.upper()} {round((s.get('accent_conf') or 0) * 100)}% · neutral {s.get('neutral_accent_score')}",
             f"Video {s.get('duration_s')} s, {s.get('words')} words" + (f" · flags: {', '.join(s['flags'])}" if s.get('flags') else ''),
             '', 'TRANSCRIPT:', (s.get('transcript') or '')[:2500]]
    ex = '; '.join(f"{x.get('msg')} [{x.get('ctx')}]" for x in (s.get('grammar_examples') or [])[:3])
    if ex: lines += ['', 'Grammar examples: ' + ex]
    return '\n'.join(lines)

def speech_summary(s):
    if s.get('error'): return f"Speaking score failed: {s['error']}"
    keys = ('overall_0_100', 'speaking_cefr', 'clarity', 'fluency', 'grammar', 'grammar_errors_per_100w', 'wpm', 'pause_ratio',
            'long_pauses', 'fillers', 'repetitions', 'accent_label', 'accent_conf', 'neutral_accent_score', 'english_prob',
            'duration_s', 'words', 'flags', 'version')
    head = ' · '.join(f"{k}={s.get(k)}" for k in keys)
    ex = '; '.join(f"{x.get('msg')} [{x.get('ctx')}]" for x in (s.get('grammar_examples') or [])[:3])
    return f"{head}\nPass mark {PASS_SPEAKING}.\nGrammar examples: {ex or '-'}\nTranscript: {(s.get('transcript') or '')[:2000]}"

def speech_spawn(k, src):
    """Start scoring in a detached, niced, time-limited process. Never raises, never blocks the caller."""
    try:
        if not SPEECH_ON or not os.path.exists(VENV_PY):
            log(speech='skipped', k=k, why='off' if not SPEECH_ON else 'no venv'); return False
        with State() as d:
            c = d['c'][k]; c.update(speech_status='pending', speech_src=src, speech_req=time.time()); c.pop('speech', None)
        os.makedirs(os.path.dirname(SPEECH_LOG), exist_ok=True); out = open(SPEECH_LOG, 'a')
        p = subprocess.Popen(['nice', '-n', '10', 'timeout', str(SPEECH_TIMEOUT), VENV_PY, os.path.join(HERE, 'talent.py'), 'score', k, src],
                             stdin=subprocess.DEVNULL, stdout=out, stderr=out, cwd=HERE, start_new_session=True, close_fds=True)
        out.close()
        threading.Thread(target=p.wait, daemon=True).start()       # reap the child so the webhook never collects zombies
        log(speech='spawned', k=k, pid=p.pid, src=os.path.basename(src)[:80]); return True
    except Exception as e:
        log(err='speech_spawn', k=k, e=str(e)[:300]); return False

def speech_job(k, src):
    """Runs inside the background process (`talent.py score <phone> <file|url>`)."""
    lk = open(os.path.join(HERE, '.speech.lock'), 'w'); fcntl.flock(lk, fcntl.LOCK_EX)   # one scoring at a time (RAM)
    try:
        import speech_score
        if src.startswith('http'):
            if not src.startswith(SB + '/storage/'): raise RuntimeError('refusing to download non-Supabase URL')
            b, _ = http('GET', src, raw=True, timeout=180)
            if len(b) > 80 * 1024 * 1024: raise RuntimeError('video too large')
            res = speech_score.score(b)
        else:
            res = speech_score.score(src)
        status = 'error' if res.get('error') else 'done'
    except Exception as e:
        res, status = {'error': str(e)[:300]}, 'error'
    finally:
        fcntl.flock(lk, fcntl.LOCK_UN); lk.close()
    with State() as d:
        c = d['c'].get(k)
        if not c: return
        if c.get('speech_src') != src: log(speech='superseded', k=k); return        # a newer video arrived meanwhile
        keep = {kk: v for kk, v in res.items() if kk not in ('detail',)}
        if keep.get('transcript'): keep['transcript'] = keep['transcript'][:1500]
        c.update(speech=keep, speech_status=status, speech_at=now()); c2 = dict(c)
    log(speech=status, k=k, overall=res.get('overall_0_100'), cefr=res.get('speaking_cefr'), e=res.get('error'))
    try:
        recruit_note(c2.get('recruit_id'), f"🎥 Video score: {res.get('overall_0_100', '-')}/100 {res.get('speaking_cefr', '')} (video attached)",
                     speech_card(res))
    except Exception as e: log(err='speech_note', k=k, e=str(e)[:200])
    try: cliq_video(c2)
    except Exception as e: log(err='cliq_video', k=k, e=str(e)[:200])
    if status == 'done':
        try: publish_video(c2); recruit_tags(c2)
        except Exception as e: log(err='publish_video', k=k, e=str(e)[:200])
    try:
        if os.path.exists(src): recruit_attach(c2.get('recruit_id'), open(src, 'rb').read(), f"video-{k}-{os.path.basename(src)}")
    except Exception as e: log(err='recruit_attach', k=k, e=str(e)[:200])
    if LIVE and not src.startswith('http') and src.startswith(MEDIA_DIR):
        try: os.remove(src)                                                    # Supabase holds the original
        except OSError: pass
    if c2.get('composite') is not None: evaluate(k)

def speech_gate(c):
    """-> 'wait' | 'pass' | 'fail' | 'unscored'"""
    if not SPEECH_ON: return 'pass'
    st = c.get('speech_status')
    if st == 'pending' and time.time() - (c.get('speech_req') or 0) < SPEECH_TIMEOUT + 300: return 'wait'
    if st == 'done':
        return 'pass' if ((c.get('speech') or {}).get('overall_0_100') or 0) >= PASS_SPEAKING else 'fail'
    return 'fail' if SPEECH_ON_ERROR == 'fail' else 'unscored'

def speech_sweep():
    """Cron: a job killed by timeout leaves 'pending' forever -> mark error and re-evaluate."""
    with State() as d:
        stale = [k for k, c in d['c'].items() if c.get('speech_status') == 'pending'
                 and time.time() - (c.get('speech_req') or 0) > SPEECH_TIMEOUT + 300]
        for k in stale: d['c'][k]['speech_status'] = 'error'
    for k in stale:
        log(speech='stale->error', k=k)
        try: evaluate(k)
        except Exception as e: log(err='speech_sweep', k=k, e=str(e)[:200])

# ---------- Messages ----------
def email_welcome_html(c):
    first = first_name(c)
    wa_line = f' to our WhatsApp <a href="{WA_LINK}">{WA_DISPLAY or WA_LINK}</a>' if WA_LINK else ' on WhatsApp'
    return f"""<p>Hi {first},</p><p>Thanks for applying to the <b>{ROLE_TITLE}</b> role at {COMPANY}.</p>
<p>The job: {CAMPAIGN_BLURB}.{(' ' + PAY_LINE + '.') if PAY_LINE else ''} Here are your 3 steps to the interview:</p>
<ol><li><b>Send a 1-minute video in English</b>{wa_line}: who you are, your call center experience, and why you perform under pressure.</li>
<li><b>Take the English test</b> (about 15 minutes) here: <a href="{apply_link(c)}">{APPLY_URL}</a>. You can also upload your video there.</li>
<li><b>Interview:</b> our recruiting team reviews your video and test, then contacts you to schedule your interview.</li></ol>
<p>{COMPANY} Recruiting<br>{HIRING_INBOX}</p>"""

def email_decline_html(c):
    first = first_name(c)
    return f"""<p>Hi {first},</p><p>Thank you for applying to {COMPANY}. This role needs fluent, conversational English on every call, so we can't move forward with your application right now.</p>
<p>We'd love to hear from you again once your English is at an advanced level. Keep practicing!</p>
<p>{COMPANY} Recruiting<br>{HIRING_INBOX}</p>"""

def basic_english(c):
    return 'native_english No, basic' in (c.get('form_summary') or '')

def wa_welcome(k, c):
    first = first_name(c)
    r = wa_template(k, TPL_STEPS, [first, apply_link(c)])
    if not r.get('dry') and 'messages' not in r:                    # steps template not approved yet -> simpler welcome
        r = wa_template(k, TPL_WELCOME, [first])
    return r

# ---------- Flow ----------
def intake(c):
    """New applicant (Meta lead or site). Idempotent per phone."""
    with State() as d:
        if not c.get('phone'): log(skip='no phone', c=c); return
        k = find(d, c['phone'], c.get('email'))
        if k: return k
        k = norm(c['phone']); c['phone'] = k; c.update(stage='new', created=now())
        d['c'][k] = c
    rid = None
    if basic_english(c):                                             # form answer "No, basic": no WhatsApp/test, polite email only
        try:
            rid = recruit_upsert(c)
            email(c.get('email'), f'{COMPANY}: your application', email_decline_html(c), 'decline_english')
        except Exception as e: log(err='decline', k=k, e=str(e)[:300])
        with State() as d: d['c'][k].update(recruit_id=rid, stage='screened_out_english')
        log(screened_out=k); return k
    for step in ('recruit', 'wa', 'email'):
        try:
            if step == 'recruit': rid = recruit_upsert(c)
            elif step == 'wa': wa_welcome(k, c)
            else: email(c.get('email'), f'{COMPANY}: 3 steps to your interview', email_welcome_html(c), 'welcome')
        except Exception as e: log(err=step, k=k, e=str(e)[:300])
    with State() as d:
        d['c'][k].update(recruit_id=rid, stage='welcomed', welcomed=now())
    log(intake=k, source=c['source'])
    with State() as d: cc = dict(d['c'][k])
    cliq_card_post(cc, '🆕 New applicant (form): steps + test link sent')
    return k

APPLYRE = re.compile(r'\b(apply|applying|sdr|bdr|job|position|trabajo|vacante|aplicar|empleo)\b', re.I)

def intake_wa(frm, contact, msg):
    """Applicant from the click-to-WhatsApp hiring ad. No form, no email yet; free-text replies only."""
    k = norm(frm)
    ref = msg.get('referral') or {}
    c = {'name': contact or 'there', 'phone': k, 'email': '', 'source': 'wa_ad', 'stage': 'new', 'created': now(), 'last_in': time.time(),
         'form_summary': 'WhatsApp ad' + (' · ad ' + ref.get('source_id', '') if ref else '')}
    with State() as d:
        if find(d, k): return
        d['c'][k] = c
    rid = None
    try: rid = recruit_upsert(c)
    except Exception as e: log(err='recruit', k=k, e=str(e)[:300])
    first = (contact or 'there').split(' ')[0]
    wa_text(k, f"Hi {first}! 👋 {BOT_NAME} from {COMPANY} HR. Thanks for applying ({ROLE_TITLE}{(', ' + PAY_LINE) if PAY_LINE else ''}).\n\n"
               "Step 1: record a 1-minute video IN ENGLISH and send it right here: who you are, your call center experience, and why you perform under pressure.\n\n"
               "Step 2: take our 15-minute English test with this same phone number:\n" + apply_link(c) +
               "\n\nStep 3: our recruiting team reviews you and schedules your interview.")
    with State() as d: d['c'][k].update(recruit_id=rid, stage='welcomed', welcomed=now(), nudged_ts=time.time())
    log(intake=k, source='wa_ad')
    with State() as d: cc = dict(d['c'][k])
    cliq_card_post(cc, '🆕 New WhatsApp applicant: steps + test link sent')

STOPRE = re.compile(r'\b(stop|unsubscribe|baja|no me escriban|remove me)\b', re.I)
def on_wa(msg, contact=''):
    """Called by wa_webhook.py for every inbound WhatsApp message. Returns True if it belonged to a candidate."""
    frm = msg.get('from', '')
    if not frm.isdigit():                                             # WhatsApp username users (no phone): never merge them or norm() a non-phone id
        log(err='wa_no_phone', uid=frm, type=msg.get('type'))
        cliq_text(f"⚠️ WhatsApp applicant WITHOUT phone number (username privacy), id={frm or '?'} · {contact or '?'}: "
                  + ((msg.get('text') or {}).get('body', '')[:300] or f"[{msg.get('type')}]") + " → answer by hand from the WhatsApp Business app")
        return True
    with State() as d:
        k = find(d, frm)
    if not k:
        txt0 = (msg.get('text') or {}).get('body', '')
        if not (msg.get('referral') or APPLYRE.search(txt0)): return False
        intake_wa(frm, contact, msg)                                 # click-to-WhatsApp ad: they wrote first, all replies are free
        return True
    with State() as d:
        d['c'][k]['last_in'] = time.time()
        c = dict(d['c'][k])
    t = msg.get('type'); txt = (msg.get('text') or {}).get('body', '')
    cliq_text(f"💬 *{c.get('name')}* +{k} ({c.get('stage')}): " + (txt[:500] if txt else f"[{t}]") + f"\n↩️ https://wa.me/{k}")
    if t == 'unsupported' and not c.get('unsup_asked'):
        wa_text(k, "We couldn't open that file 🙏 Please send your video again as a normal video from your gallery (not view-once), about 1 minute, max 16 MB.")
        with State() as d: d['c'][k]['unsup_asked'] = now()
    if txt and STOPRE.search(txt):
        with State() as d: d['c'][k]['stage'] = 'stopped'
        log(stop=k); return True
    if (c.get('rp') or {}).get('round') is not None and not (c.get('rp') or {}).get('done') and t in ('audio', 'video', 'text'):
        try:
            import roleplay
            if roleplay.on_answer(sys.modules[__name__], k, c, msg): return True
        except Exception as e: log(err='roleplay', k=k, e=str(e)[:200])
    if txt and c.get('consent_asked') and not c.get('consent') and CONSENT_RE.search(txt):
        with State() as d: d['c'][k].update(consent=now()); c = dict(d['c'][k])
        log(consent=k)
        recruit_note(c.get('recruit_id'), 'Consent: website profile', f'Candidate replied "{txt[:80]}" on WhatsApp at {now()}')
        try:
            publish_video(c)
            if c.get('mp_id'):
                h = {'apikey': SBK, 'Authorization': 'Bearer ' + SBK, 'Prefer': 'return=minimal'}
                if True:                                          # every consented candidate goes up (approved)
                    http('PATCH', f"{SB}/rest/v1/talent_profiles?id=eq.{c['mp_id']}", {'status': 'approved'}, h)
            recruit_tags(c)
        except Exception as e: log(err='consent_publish', e=str(e)[:200])
        wa_text(k, f'Thank you! ✅ Your profile is going up on our talent site. — {sig()}')
        return True
    doc = msg.get('document') or {}
    if doc and not doc.get('mime_type', '').startswith('video'):          # CV / resume (PDF, Word, image)
        try:
            data, mime = wa_media(doc['id'])
            ext = (doc.get('filename') or 'cv.pdf').rsplit('.', 1)[-1][:5].lower() or 'pdf'
            path = sb_upload(f"recruiting/{k}/cv-{int(time.time())}.{ext}", data, mime)
            recruit_attach(c.get('recruit_id'), data, f"CV-{k}.{ext}", mime or 'application/pdf', 'Resume')
            with State() as d: d['c'][k].update(resume_path=path, resume_at=now())
            if 'pdf' in (mime or '') or ext == 'pdf': cv_analyze(c, data)
            recruit_note(c.get('recruit_id'), 'CV received on WhatsApp', f'Stored in Supabase {VIDEO_BUCKET}/{path}; attached as Resume')
            log(cv_in=k, path=path)
            wa_text(k, "Got your CV, thank you! 📄" + ("" if c.get('video_path') else
                       "\n\nNow send your 1-minute video IN ENGLISH right here (it's what clients see)."))
        except Exception as e:
            log(err='cv', k=k, e=str(e)[:200]); wa_text(k, 'We could not open your CV. Please send it again as a PDF.')
        return True
    if msg.get('image'):
        try:
            data, mime = wa_media(msg['image']['id'])
            path = sb_upload(f"recruiting/{k}/img-{int(time.time())}.jpg", data, mime or 'image/jpeg')
            cap = (msg['image'].get('caption') or '')[:200]
            cliq_text(f"🖼️ *{c.get('name')}* +{k} sent an image{(': ' + cap) if cap else ''}\n{sb_sign(path)}\n↩️ https://wa.me/{k}")
            log(image_in=k, path=path)
            if time.time() - (c.get('faq_ts') or 0) > 20 * 60:
                wa_text(k, "Thanks for the screenshot! 🙏 If the link gave you an error, use this one (open it in Chrome):\n"
                           + apply_link(c) + f"\n\nStill not working? Tell us here what you see and we'll fix it. — {sig()}")
                with State() as d: d['c'][k]['faq_ts'] = time.time()
        except Exception as e: log(err='image', k=k, e=str(e)[:200])
        return True
    if msg.get('audio'):                                                 # voice note: score it, but we still need the video
        try:
            data, mime = wa_media(msg['audio']['id'])
            ts = int(time.time()); path = sb_upload(f"recruiting/{k}/wa-voice-{ts}.ogg", data, mime or 'audio/ogg')
            local = os.path.join(MEDIA_DIR, f'{k}-voice-{ts}.ogg'); os.makedirs(MEDIA_DIR, exist_ok=True)
            with open(local, 'wb') as fh: fh.write(data)
            with State() as d:
                d['c'][k].update(audio_path=path, audio_at=now())
                if not d['c'][k].get('video_path') and not d['c'][k].get('rp'): d['c'][k].update(speech_status='pending', speech_src=local, speech_req=time.time())
            if not c.get('video_path') and not c.get('rp'): speech_spawn(k, local)
            log(audio_in=k, path=path)
            has_video = bool(c.get('video_path') or c.get('video_url'))
            if c.get('rp'):                                   # roleplay voice answers: keep them, never re-ask anything
                with State() as d:
                    d['c'][k].setdefault('rp', {}).setdefault('late_answers', []).append({'path': path, 't': now()})
                log(rp_late_answer=k, path=path)
            elif not has_video and not c.get('audio_asked_video'):
                wa_text(k, "Got your voice note, thanks! 🎙️ We're scoring your English now.\n\n"
                           "We still need a short VIDEO (about 1 minute, in English) sent here: clients want to see you. "
                           "You can also send your CV as a PDF.")
                with State() as d: d['c'][k]['audio_asked_video'] = now()
        except Exception as e: log(err='audio', k=k, e=str(e)[:200])
        return True
    media = msg.get('video') or (msg.get('document') if (msg.get('document') or {}).get('mime_type', '').startswith('video') else None)
    if media:
        try:
            data, mime = wa_media(media['id'])
        except Exception as e:
            log(err='media', k=k, e=str(e)[:200]); wa_text(k, 'We could not download your video. Please send it again (max 16 MB, about 1 minute).'); return True
        ext = 'mp4' if 'mp4' in (mime or '') else (mime or 'video/mp4').split('/')[-1]
        ts = int(time.time())
        path = sb_upload(f"recruiting/{k}/wa-intro-{ts}.{ext}", data, mime)
        local = None
        try:
            os.makedirs(os.path.join(MEDIA_DIR, k), mode=0o700, exist_ok=True)
            local = os.path.join(MEDIA_DIR, k, f"wa-intro-{ts}.{re.sub(r'[^a-z0-9]', '', ext)[:5] or 'mp4'}")
            with open(local, 'wb') as fh: fh.write(data)
            os.chmod(local, 0o600)
        except Exception as e: log(err='media_local', k=k, e=str(e)[:200]); local = None
        with State() as d:
            d['c'][k].update(video_path=path, video_at=now(), stage='video_in' if d['c'][k].get('stage') in ('welcomed', 'new', 'reminded') else d['c'][k]['stage'])
            c = dict(d['c'][k])
        recruit_note(c.get('recruit_id'), 'WhatsApp intro video received', f'Stored in Supabase {VIDEO_BUCKET}/{path}')
        if local: speech_spawn(k, local)
        if c.get('composite') is not None: return evaluate(k) or True
        if env.get('TALENT_ROLEPLAY', '1') == '1' and not c.get('rp'):
            wa_text(k, f"Got your video, thank you! 🎥 — {sig()}\n\nStep 2: a quick 5-round phone roleplay right here 👇")
            import roleplay; roleplay.start(sys.modules[__name__], k)
            return True
        wa_text(k, f"Got your video, thank you! 🎥 — {sig()}\n\nStep 2 of 3: take our English test (about 15 minutes). Use this same phone number:\n"
                   + apply_link(c) + "\n\nFinish it today. Step 3: our recruiting team reviews you and schedules your interview.\n\n📄 If you have a CV, send it here as a PDF too.")
        return True
    if txt and ASKRE.search(txt) and time.time() - (c.get('faq_ts') or 0) > 20 * 60 and c.get('stage') not in ('stopped',):
        wa_text(k, next_step_reply(c))
        with State() as d: d['c'][k].update(faq_ts=time.time(), nudged_ts=time.time())
        log(wa_in=k, type=t, text=txt[:200], replied='next_step'); return True
    if c.get('stage') in ('welcomed', 'reminded') and time.time() - c.get('nudged_ts', 0) > 6 * 3600:
        wa_text(k, 'Thanks for your message! To move forward, record a 1-minute video IN ENGLISH and send it right here in this chat: '
                   'who you are, your call center experience, and why you perform under pressure.')
        with State() as d: d['c'][k]['nudged_ts'] = time.time()
    log(wa_in=k, type=t, text=txt[:200])
    return True

def on_test(p):
    """Results POSTed by the Apply page (or found in storage). p: name,email,phone,assessment{...},video_url,resume_url."""
    a = p.get('assessment') or {}
    k = None
    with State() as d: k = find(d, p.get('phone'), p.get('email'))
    if not k:
        k = intake({'name': p.get('name'), 'email': p.get('email'), 'phone': p.get('phone'), 'source': 'site',
                    'form_summary': f"Site apply · role {p.get('role') or '-'} · English self {p.get('english') or '-'}"})
        if not k: return {'ok': False, 'why': 'no phone'}
    with State() as d:
        c = d['c'][k]
        if a: c.update(composite=a.get('composite_score'), english=a.get('english_score'), sales=a.get('sales_score'),
                       wpm=a.get('typing_wpm'), tier=a.get('tier'), test_at=now())
        if p.get('video_url'): c['video_url'] = p['video_url']
        if p.get('resume_url'): c['resume_url'] = p['resume_url']; cv_new = p['resume_url'] if not c.get('cv_summary') else None
        else: cv_new = None
        site_video = (p.get('video_url') or '') if not c.get('video_path') and c.get('speech_src') != p.get('video_url') else ''
    if site_video.startswith(SB + '/storage/'): speech_spawn(k, site_video)
    if cv_new and cv_new.lower().endswith('.pdf'):
        try:
            with State() as d: cc = dict(d['c'][k])
            cv_analyze(cc, urllib.request.urlopen(cv_new, timeout=60).read())
        except Exception as e: log(err='cv_fetch', e=str(e)[:200])
    return evaluate(k) or {'ok': True}

def evaluate(k):
    with State() as d: c = dict(d['c'][k])
    if c.get('stage') in ('passed', 'failed', 'stopped') or c.get('composite') is None: return None
    has_video = bool(c.get('video_path') or c.get('video_url'))
    passed = (c['composite'] or 0) >= PASS_COMPOSITE and (c.get('english') or 0) >= PASS_ENGLISH
    gate = speech_gate(c) if has_video else None
    if passed and gate == 'wait':                     # speaking score still running; speech_job() calls evaluate() again
        log(waiting_speech=k); return {'ok': True, 'stage': 'scoring'}
    rid = c.get('recruit_id')
    recruit_note(rid, 'English test result', f"Composite {c['composite']} · English {c.get('english')} · Sales {c.get('sales')} · Typing {c.get('wpm')} WPM · pass={passed}")
    if not passed:
        recruit_status(rid, 'Unqualified')
        with State() as d: d['c'][k]['stage'] = 'failed'
        recruit_tags(dict(c, stage='failed')); cliq_card_post(dict(c, stage='failed'), f"❌ Test not passed · composite {c['composite']}")
        log(failed=k, composite=c['composite']); return {'ok': True, 'stage': 'failed'}
    if not has_video:
        r = wa_text(k, 'Great test result! 🔥 Last step: send your 1-minute video IN ENGLISH right here in this chat.')
        if r.get('_err'):   # 24h window closed -> approved template asking for the video
            wa_template(k, TPL_REMINDER, [first_name(c)])
        with State() as d: d['c'][k]['stage'] = 'test_passed_no_video'
        return {'ok': True, 'stage': 'needs_video'}
    if gate == 'fail':                                # test passed, speaking below TALENT_PASS_SPEAKING (or error + fail mode)
        recruit_status(rid, 'Unqualified')
        with State() as d: d['c'][k].update(stage='failed', failed_reason='speaking')
        log(failed=k, reason='speaking', speaking=(c.get('speech') or {}).get('overall_0_100'), status=c.get('speech_status'))
        return {'ok': True, 'stage': 'failed'}
    with State() as d: d['c'][k].update(stage='passed', passed_at=now())   # mark BEFORE side-effects -> never repeats
    recruit_status(rid, 'Qualified'); cliq_card(c); marketplace_pending(c); interview_task(c)
    wa_text(k, "You passed! ✅ Our recruiting team will contact you here on WhatsApp to schedule your interview.")  # outside 24h it just fails; Cliq team calls
    log(passed=k); return {'ok': True, 'stage': 'passed'}

# ---------- WhatsApp follow-ups (free text only inside 24h of the candidate's last message) ----------
TEST_HOW = ("On the test page: fill name/email/phone, answer the 3 short modules (English, Sales, Typing), "
            "record a short voice intro OR upload your CV, then press Submit.")
def wa_followups():
    nowt = time.time()
    with State() as d: cs = {k: dict(c) for k, c in d['c'].items()}
    for k, c in cs.items():
        li = c.get('last_in')
        if not li or nowt - li > 22 * 3600: continue           # window closed (or never wrote): no free text possible
        st = c.get('stage'); first = (c.get('name') or 'there').split(' ')[0]
        has_video = bool(c.get('video_path') or c.get('video_url'))
        msg = flag = None
        if st in ('welcomed', 'reminded') and not has_video:
            if not c.get('fu1') and nowt - li > 3 * 3600:
                flag, msg = 'fu1', (f"Hi {first}! Quick reminder from {COMPANY} 🙂 Step 1 is a 1-minute video IN ENGLISH, sent right here in this chat: "
                                    "who you are, your call center experience, and why you perform under pressure. Your spot is still open today.")
            elif c.get('fu1') and not c.get('fu2') and nowt - li > 18 * 3600:
                flag, msg = 'fu2', (f"{first}, last reminder for today: send your 1-minute English video here and you go straight to the English test:\n"
                                    + apply_link(c) + "\n" + TEST_HOW)
        elif has_video and c.get('composite') is None and st in ('video_in',):
            if not c.get('fu_test') and nowt - (c.get('video_ts') or li) > 3 * 3600:
                flag, msg = 'fu_test', (f"Great video, {first}! 🎥 Next: the 15-minute English test (same phone number):\n" + apply_link(c) + "\n" + TEST_HOW)
        if msg:
            with State() as d: d['c'][k][flag] = now()   # flag BEFORE sending (idempotent)
            r = wa_text(k, msg)
            log(followup=k, which=flag, ok=not r.get('_err'))

# ---------- Optional: share candidates with a client (both OFF by default) ----------
def mirror_sweep():
    """TALENT_CLIENT_ATS_MIRROR=1: copy candidates into the client's own Zoho Recruit (client_ats_mirror.py)."""
    if not LIVE or env.get('TALENT_CLIENT_ATS_MIRROR', '0') != '1': return
    import client_ats_mirror
    with State() as d: ks = list(d['c'].keys())
    for k in ks: client_ats_mirror.mirror(sys.modules[__name__], k)

def client_cliq_sweep():
    """TALENT_CLIENT_SHARE=1: post passers (alias + scores + reel, no PII, no rates) to the client's chat (client_share.py)."""
    if not LIVE or env.get('TALENT_CLIENT_SHARE', '0') != '1': return
    try:
        import client_share; client_share.sweep(sys.modules[__name__])
    except Exception as e: log(err='client_share', e=str(e)[:200])

# ---------- Cron ----------
def poll_meta():
    for job in JOBS: poll_form(job)

def poll_form(job):
    fid = job['form_id']
    with State() as d: since = d.setdefault('form_since', {}).get(fid, 0)
    url = G + fid + '/leads?' + urllib.parse.urlencode({'fields': 'created_time,field_data', 'limit': 100, 'access_token': env.get('META_LEADS_TOKEN') or WA_T,
          'filtering': json.dumps([{'field': 'time_created', 'operator': 'GREATER_THAN', 'value': since}])})
    r = http('GET', url); newest = since
    for lead in r.get('data', []):
        f = {x['name']: (x.get('values') or [''])[0] for x in lead.get('field_data', [])}
        ts = int(time.mktime(time.strptime(lead['created_time'][:19], '%Y-%m-%dT%H:%M:%S'))); newest = max(newest, ts)
        extra = ' · '.join(f'{k} {v}' for k, v in f.items() if k not in ('full_name', 'email', 'phone_number'))
        intake({'name': f.get('full_name'), 'email': f.get('email'), 'phone': f.get('phone_number'), 'source': 'meta', 'meta_lead_id': lead['id'],
                'job_id': job['job_id'], 'job_title': job.get('title', ''), 'form_summary': f"{job.get('title', '')}: {extra}"})
    if r.get('_err'): log(err='meta', form=fid, r=r)
    with State() as d: d['form_since'][fid] = newest

def digest():
    """Hourly Cliq summary, only when something changed since the last one."""
    with State() as d:
        stages = {}
        for c in d['c'].values(): stages[c.get('stage', '?')] = stages.get(c.get('stage', '?'), 0) + 1
        sig = json.dumps(stages, sort_keys=True)
        if sig == d.get('digest_sig'): return
        d['digest_sig'] = sig
        stuck = [c.get('name') or k for k, c in d['c'].items() if c.get('stage') in ('welcomed', 'reminded', 'video_in')
                 and c.get('created') and time.time() - time.mktime(time.strptime(c['created'], '%Y-%m-%dT%H:%M:%SZ')) + time.timezone > 48 * 3600]
    order = ['welcomed', 'reminded', 'video_in', 'test_passed_no_video', 'passed', 'failed', 'stopped']
    txt = '📊 *Recruiting pipeline*: ' + ' · '.join(f'{s} {stages[s]}' for s in order if s in stages)
    if stuck: txt += "\n⏳ Stuck >48h: " + ', '.join(stuck[:10])
    if not LIVE: log(dry='digest', txt=txt); return
    import cliq
    cliq.post(CLIQ_CHANNEL, {'text': txt}); log(digest=txt)

def reminders():
    with State() as d: todo = [k for k, c in d['c'].items() if c.get('stage') == 'welcomed' and c.get('welcomed')
                               and time.time() - time.mktime(time.strptime(c['welcomed'], '%Y-%m-%dT%H:%M:%SZ')) + time.timezone > 24 * 3600]
    for k in todo:
        with State() as d: c = d['c'][k]; c['stage'] = 'reminded'
        wa_template(k, TPL_REMINDER, [first_name(c)])

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'run'
    if cmd == 'run':
        _rl = open(os.path.join(HERE, '.run.lock'), 'w')   # one `run` at a time (cron */2 has no flock)
        try: fcntl.flock(_rl, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: print('run already in progress'); sys.exit(0)
        poll_meta(); reminders(); speech_sweep(); wa_followups(); mirror_sweep(); client_cliq_sweep()
    elif cmd == 'score': speech_job(sys.argv[2], sys.argv[3]); sys.exit(0)
    elif cmd == 'rescore':     # manual: talent.py rescore <phone> <file|our Supabase URL>  (run with .venv/bin/python)
        with State() as d:
            kk = find(d, sys.argv[2]); d['c'][kk].update(speech_status='pending', speech_src=sys.argv[3], speech_req=time.time())
        speech_job(kk, sys.argv[3]); sys.exit(0)
    elif cmd == 'digest': digest()
    elif cmd == 'rpscore':      # venv python: transcribe + grade roleplay voice notes (one scorer at a time)
        lk = open(os.path.join(HERE, '.speech.lock'), 'w'); fcntl.flock(lk, fcntl.LOCK_EX)
        import roleplay; roleplay.score_pending(sys.modules[__name__])
    elif cmd == 'rpstart':      # talent.py rpstart <phone>
        import roleplay; print(roleplay.start(sys.modules[__name__], norm(sys.argv[2])))
    elif cmd == 'status':
        with State() as d:
            for k, c in d['c'].items(): print(k, c.get('stage'), c.get('name'), c.get('composite'), bool(c.get('video_path') or c.get('video_url')),
                                              'speech=%s/%s' % (c.get('speech_status'), (c.get('speech') or {}).get('overall_0_100')))
    print('LIVE' if LIVE else 'DRY', 'allow=', sorted(ALLOW) or 'ALL')
