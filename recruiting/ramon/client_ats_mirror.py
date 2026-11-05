"""Optional: mirror candidates into a CLIENT's own Zoho Recruit (TALENT_CLIENT_ATS_MIRROR=1).
Idempotent: called after every pipeline event; state keys ats_* track what was already sent.
The client's Recruit is a different Zoho org: CLIENT_RECRUIT_CLIENT_ID / _CLIENT_SECRET / _REFRESH_TOKEN / _JOB_ID.
Decide this per client BEFORE turning it on: once a record is in their ATS, it is theirs. Pay rates are never sent."""
import json, os, time, urllib.request, urllib.parse, urllib.error
B = 'https://recruit.zoho.com/recruit/v2/'
_tok = {'t': None, 'exp': 0}
_T = {}

def _env():
    return _T['env'] if 'env' in _T else os.environ

def token():
    if _tok['t'] and time.time() < _tok['exp']: return _tok['t']
    e = _env()
    d = json.load(urllib.request.urlopen('https://accounts.zoho.com/oauth/v2/token', urllib.parse.urlencode(
        {'grant_type': 'refresh_token', 'client_id': e['CLIENT_RECRUIT_CLIENT_ID'], 'client_secret': e['CLIENT_RECRUIT_CLIENT_SECRET'],
         'refresh_token': e['CLIENT_RECRUIT_REFRESH_TOKEN']}).encode(), timeout=30))
    _tok.update(t=d['access_token'], exp=time.time() + 3000); return _tok['t']

def call(m, path, body=None, raw=None, ctype='application/json'):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(B + path, method=m, data=data, headers={'Authorization': 'Zoho-oauthtoken ' + token(), 'Content-Type': ctype})
    try:
        r = urllib.request.urlopen(req, timeout=120).read(); return json.loads(r) if r else {}
    except urllib.error.HTTPError as e: return {'_http': e.code, 'body': e.read()[:300].decode('utf-8', 'replace')}

def attach(rid, data, fname, mime, cat):
    b = '----atsmirror' + str(int(time.time()))
    body = (f'--{b}\r\nContent-Disposition: form-data; name="attachments_category"\r\n\r\n{cat}\r\n'
            f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{fname}"\r\nContent-Type: {mime}\r\n\r\n').encode() + data + f'\r\n--{b}--\r\n'.encode()
    return call('POST', f'Candidates/{rid}/Attachments', raw=body, ctype='multipart/form-data; boundary=' + b)

def mirror(T, k):
    """T = the talent module (state, helpers). Never raises."""
    _T['env'] = T.env
    try:
        with T.State() as d:
            c = dict(d['c'].get(k) or {})
        if not c or c.get('stage') in ('screened_out_english',) or 'TEST' in (c.get('name') or '').upper(): return
        up = {}
        sp = c.get('speech') or {}
        nm = (c.get('name') or 'Applicant').split()
        status = {'passed': 'Qualified', 'failed': 'Unqualified'}.get(c.get('stage'), 'New')
        if not c.get('ats_id'):
            r = call('POST', 'Candidates', {'data': [{'First_Name': nm[0], 'Last_Name': ' '.join(nm[1:]) or nm[0], 'Mobile': '+' + k,
                     'Email': c.get('email') or None, 'Source': T.COMPANY, 'Candidate_Status': status,
                     'Current_Job_Title': T.ROLE_TITLE}], 'trigger': []})
            rid = (((r.get('data') or [{}])[0]).get('details') or {}).get('id')
            if not rid: T.log(err='ats_create', k=k, r=str(r)[:200]); return
            job = _env().get('CLIENT_RECRUIT_JOB_ID')
            if job: call('PUT', 'Candidates/actions/associate', {'data': [{'ids': [rid], 'jobids': [job], 'comments': f'Sourced and pre-screened by {T.COMPANY}'}]})
            up['ats_id'] = rid; c['ats_id'] = rid
        rid = c['ats_id']
        if c.get('ats_status') != status:
            call('PUT', 'Candidates', {'data': [{'id': rid, 'Candidate_Status': status}], 'trigger': []}); up['ats_status'] = status
        tags = [f'Via {T.COMPANY}']   # never send pay rates to a client
        if sp.get('overall_0_100') is not None:
            o = sp['overall_0_100']; tags.append('Speaking 80+' if o >= 80 else 'Speaking 60-79' if o >= 60 else 'Speaking under 60')
        if c.get('stage') == 'passed': tags += ['Test passed', 'Interview pending']
        elif c.get('stage') == 'failed': tags.append('Test failed')
        if c.get('ats_tags') != tags:
            call('POST', 'Candidates/actions/add_tags?' + urllib.parse.urlencode({'ids': rid, 'tag_names': ','.join(tags)})); up['ats_tags'] = tags
        notes = set(c.get('ats_notes') or [])
        if c.get('speech_status') == 'done' and 'speech' not in notes:
            call('POST', 'Notes', {'data': [{'Note_Title': f"🎥 Video score {sp.get('overall_0_100')}/100 {sp.get('speaking_cefr') or ''}",
                 'Note_Content': T.speech_card(sp) if hasattr(T, 'speech_card') else json.dumps(sp)[:1500], 'Parent_Id': rid, 'se_module': 'Candidates'}]})
            notes.add('speech')
        if c.get('composite') is not None and 'test' not in notes:
            call('POST', 'Notes', {'data': [{'Note_Title': f'English test ({T.COMPANY})', 'Note_Content':
                 f"Composite {c.get('composite')} · English {c.get('english')}% · Sales {c.get('sales')}% · Typing {c.get('wpm')} WPM", 'Parent_Id': rid, 'se_module': 'Candidates'}]})
            notes.add('test')
        up['ats_notes'] = sorted(notes)
        for key, path, cat, mime, fn in (('ats_video', c.get('video_path'), 'Others', 'video/mp4', f'video-{k}.mp4'),
                                         ('ats_cv', c.get('resume_path'), 'Resume', 'application/pdf', f'CV-{k}.pdf')):
            if path and not c.get(key):
                url = T.sb_sign(path, 1)
                if url:
                    data = urllib.request.urlopen(url, timeout=180).read()
                    r = attach(rid, data, fn, mime, cat); up[key] = T.now(); T.log(ats_attach=k, what=key, r=str(r)[:120])
        with T.State() as d:
            if k in d['c']: d['c'][k].update(up)
        T.log(ats=k, rid=rid, status=status)
    except Exception as e:
        try: T.log(err='ats', k=k, e=str(e)[:200])
        except Exception: pass
