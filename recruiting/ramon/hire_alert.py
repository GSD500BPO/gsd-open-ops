"""Internal alert for "Hire" / "Make an offer" clicks on your public talent page (Supabase table talent_hire_requests).
New rows -> team Cliq channel + email to TALENT_HIRING_INBOX (CC = TALENT_MAIL_CC). Run from cron every 2 minutes."""
# Hardening: state (since + per-request per-channel markers) is saved BEFORE each send; each channel has its own
# try; a request gets at most ONE Cliq post and ONE email ever (a failed send is logged, never retried automatically).
import json, os, sys, fcntl
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import outbound_guard as og
og.assert_not_paused('hire_alert')
STATE = os.path.join(HERE, 'hire_alert_state.json')
_lk = open(STATE + '.lock', 'w')
try: fcntl.flock(_lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError: sys.exit(0)            # previous run still going
import talent

H = {'apikey': talent.SBK, 'Authorization': 'Bearer ' + talent.SBK}
seen = json.load(open(STATE)) if os.path.exists(STATE) else {'since': talent.now()}   # first run: only new requests
seen.setdefault('done', {})
def save():
    tmp = STATE + '.tmp'; json.dump(seen, open(tmp, 'w')); os.replace(tmp, STATE)
rows = talent.http('GET', f"{talent.SB}/rest/v1/talent_hire_requests?select=*&created_at=gt.{seen['since']}&order=created_at.asc", None, H)
for r in rows if isinstance(rows, list) else []:
    rid = str(r['id']); mk = seen['done'].setdefault(rid, {})
    seen['since'] = max(seen['since'], r['created_at']); save()   # advance BEFORE any send
    if mk.get('cliq') and mk.get('email'): continue
    m = r.get('metadata') or {}
    prof = {}
    if r.get('talent_profile_id'):
        try: p = talent.http('GET', f"{talent.SB}/rest/v1/talent_profiles?id=eq.{r['talent_profile_id']}&select=display_name,title,hourly_rate,bio", None, H)
        except Exception as e: p = []; talent.log(err='hire_profile', rid=rid, e=str(e)[:200])
        prof = p[0] if isinstance(p, list) and p else {}
    who = prof.get('display_name') or m.get('agent_name') or '?'
    kind = m.get('request_type') or r.get('request_type') or 'hire'
    offer = r.get('offer_amount') or m.get('offer_amount')
    lines = [f"*{r.get('client_name')}*  ·  {r.get('client_email')}  ·  {r.get('client_phone') or 'no phone'}",
             f"Wants: *{who}* ({prof.get('title') or m.get('agent_title') or '-'}) · listed ${prof.get('hourly_rate') or m.get('agent_rate')}/hr"
             + (f" · OFFER ${offer}/hr" if offer else '') + f" · {kind}" + (' · SAMPLE profile' if m.get('is_sample') else ''),
             f"Job: {(r.get('job_description') or '-')[:600]}",
             f"Call/WhatsApp them today. Request id {r['id']}"]
    msg = {'text': '\n'.join(lines), 'card': {'title': '💼 New client wants to hire from /talent', 'theme': 'modern-inline'}}
    if not mk.get('cliq'):
        mk['cliq'] = talent.now(); save()          # marker BEFORE posting
        try:
            import cliq
            talent.log(hire_cliq=str(cliq.post(talent.CLIQ_CHANNEL, msg))[:200])
        except Exception as e: talent.log(err='hire_cliq', rid=rid, e=str(e)[:200]); mk['cliq_err'] = str(e)[:120]; save()
    if not mk.get('email'):
        mk['email'] = talent.now(); save()         # marker BEFORE sending (talent.email reserves its outbound_guard slot)
        html = '<p>' + '<br>'.join(l.replace('*', '') for l in lines) + '</p>'
        try: talent.email(talent.HIRING_INBOX, f'💼 Talent hire request: {r.get("client_name")} wants {who}', html, 'hire_alert')
        except Exception as e: talent.log(err='hire_email', rid=rid, e=str(e)[:200]); mk['email_err'] = str(e)[:120]; save()
    print('alerted', r['id'], who)
