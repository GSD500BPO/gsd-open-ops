"""WhatsApp Cloud API webhook receiver for Ramón.

- GET  = Meta's verification handshake (hub.verify_token must equal WA_VERIFY_TOKEN).
- POST = inbound messages. The body is checked against X-Hub-Signature-256 with WA_APP_SECRET, every message id is
  de-duplicated (Meta retries when you are slow), and each message is handed to talent.on_wa().
  Messages that don't belong to a candidate are only logged: plug your own handler into `other()`.

Run it on localhost behind a TLS reverse proxy / tunnel and register https://<your-host>/<path> in the Meta app."""
import hashlib, hmac, json, os, threading, time, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import talent

HERE = os.path.dirname(os.path.abspath(__file__))
LOGDIR = os.path.join(HERE, 'logs'); os.makedirs(LOGDIR, exist_ok=True)
LOG = os.path.join(LOGDIR, 'wa-inbound.jsonl')
VT = talent.env.get('WA_VERIFY_TOKEN', '')
APPSEC = talent.env.get('WA_APP_SECRET', '')
PH = talent.WA_PH

_SEEN = {}; _LOCK = threading.Lock()


def seen(mid):
    if not mid: return False
    with _LOCK:
        now = time.time()
        for k in [k for k, t in _SEEN.items() if now - t > 86400]: _SEEN.pop(k, None)
        if mid in _SEEN: return True
        _SEEN[mid] = now
        return False


def write(rec):
    rec['t'] = time.strftime('%FT%TZ', time.gmtime())
    open(LOG, 'a').write(json.dumps(rec, ensure_ascii=False) + '\n')


def other(msg, contact):
    """Inbound message from someone who is not a candidate. Default: log only (no auto-reply)."""
    write({'other': msg.get('type'), 'from_suffix': (msg.get('from') or '')[-4:]})


def handle(msg, contact):
    try:
        if talent.on_wa(msg, contact): return
    except Exception as e:
        write({'err': 'talent ' + str(e)[:200]})
    other(msg, contact)


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if VT and hmac.compare_digest(q.get('hub.verify_token', [''])[0], VT):
            self.send_response(200); self.end_headers(); self.wfile.write(q.get('hub.challenge', [''])[0].encode())
        else:
            self.send_response(403); self.end_headers()

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', 0) or 0))
        if not APPSEC:
            self.send_response(503); self.end_headers(); return          # refuse to run unauthenticated
        good = 'sha256=' + hmac.new(APPSEC.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(self.headers.get('X-Hub-Signature-256', ''), good):
            self.send_response(403); self.end_headers(); return
        self.send_response(200); self.end_headers()
        try:
            d = json.loads(body)
            for e in d.get('entry', []):
                for c in e.get('changes', []):
                    v = c.get('value', {})
                    if PH and v.get('metadata', {}).get('phone_number_id') != PH: continue
                    names = {(x.get('wa_id') or x.get('user_id') or ''): x.get('profile', {}).get('name', '') for x in v.get('contacts', [])}
                    for m in v.get('messages', []):
                        if seen(m.get('id')): continue
                        if not m.get('from'):                    # username-only users: no phone number in the payload
                            uid = m.get('from_user_id') or m.get('user_id') or next((x.get('user_id') for x in v.get('contacts', []) if x.get('user_id')), '')
                            if uid: m['from'] = uid
                        handle(m, names.get(m.get('from'), ''))
                    for x in v.get('statuses', []):
                        write({'status': x.get('status'), 'id': x.get('id'), 'errors': x.get('errors')})
        except Exception as ex:
            write({'err': str(ex)[:200]})

    def log_message(self, *a): pass


if __name__ == '__main__':
    ThreadingHTTPServer((talent.env.get('WA_WEBHOOK_HOST', '127.0.0.1'), int(talent.env.get('WA_WEBHOOK_PORT', '8787'))), H).serve_forever()
