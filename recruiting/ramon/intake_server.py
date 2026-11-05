# Receives English-test results from your apply page (POST JSON) and serves the web roleplay at /talent/roleplay.
# Bind it to localhost and put it behind a reverse proxy / tunnel that terminates TLS.
import json, os, time, re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import talent

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINS = {o.strip() for o in talent.env.get('TALENT_CORS_ORIGINS', '').split(',') if o.strip()}   # e.g. https://yourdomain.com
ORIGIN_RE = talent.env.get('TALENT_CORS_ORIGIN_REGEX', '')                                          # optional, e.g. preview domains
hits = {}

class H(BaseHTTPRequestHandler):
    def cors(self):
        o = self.headers.get('Origin', '')
        if o in ORIGINS or (ORIGIN_RE and re.match(ORIGIN_RE, o)):
            self.send_header('Access-Control-Allow-Origin', o)
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    def do_OPTIONS(self):
        self.send_response(204); self.cors(); self.end_headers()
    # ---- web roleplay (/talent/roleplay) ----
    def _rp(self):
        path = self.path.split('?')[0].rstrip('/')
        m = re.search(r'/roleplay(?:/(start|asked|answer|finish|log))?$', path)
        return m.group(1) or 'page' if m else None
    def _json(self, code, obj):
        self.send_response(code); self.send_header('Content-Type', 'application/json'); self.send_header('Cache-Control', 'no-store'); self.end_headers()
        self.wfile.write(json.dumps(obj).encode())
    def do_GET(self):
        if self._rp() == 'page':
            import roleplay
            sc = roleplay.SCENARIO
            body = open(os.path.join(HERE, 'roleplay.html'), encoding='utf-8').read()
            for k, v in (('{{COMPANY}}', talent.COMPANY), ('{{BOT_NAME}}', talent.BOT_NAME), ('{{SCENARIO_INTRO}}', sc.get('web_intro', '')),
                         ('{{SCENARIO_GOAL}}', sc.get('goal_html', '')), ('{{PERSONA}}', roleplay.PERSONA)):
                body = body.replace(k, v)
            body = body.encode()
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.send_header('Cache-Control', 'no-store')
            self.send_header('Permissions-Policy', 'microphone=(self)'); self.end_headers(); self.wfile.write(body); return
        self.send_response(404); self.end_headers()
    def do_rp_post(self, act, ip):
        import rp_web, urllib.parse
        n = int(self.headers.get('Content-Length', 0) or 0)
        key = 'rp:' + ip; hits[key] = [t for t in hits.get(key, []) if time.time() - t < 3600] + [time.time()]
        local = ip == '127.0.0.1' and not self.headers.get('X-Forwarded-For')   # ssh-tunnel test runs
        if (len(hits[key]) > 200 and not local) or n > 12_000_000: return self._json(429, {'ok': False})
        if act == 'answer':
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            return self._json(200, rp_web.answer(q.get('sid', [''])[0], int(q.get('round', ['-1'])[0]), self.rfile.read(n), self.headers.get('Content-Type', '')))
        p = json.loads(self.rfile.read(n) or b'{}')
        if act == 'start':
            talent.log(rpweb_ip=ip, xff=self.headers.get('X-Forwarded-For'))
            st = 'rps:' + ip; hits[st] = [t for t in hits.get(st, []) if time.time() - t < 3600] + [time.time()]
            if len(hits[st]) > 15 and not local: return self._json(429, {'ok': False})
            return self._json(200, rp_web.start(p.get('name'), p.get('phone'), p.get('test')))
        if act == 'asked': rp_web.asked(p.get('sid', ''), int(p.get('round', -1))); return self._json(200, {'ok': True})
        if act == 'log': talent.log(rpweb_client=str(p)[:600]); return self._json(200, {'ok': True})
        if act == 'finish': return self._json(200, rp_web.finish(p.get('sid', '')))
        return self._json(404, {'ok': False})
    def do_POST(self):
        ip = self.headers.get('X-Forwarded-For', self.client_address[0]).split(',')[0]
        act = self._rp()
        if act and act != 'page':
            try: return self.do_rp_post(act, ip)
            except Exception as e:
                talent.log(err='rpweb', e=str(e)[:300]); return self._json(400, {'ok': False})
        hits[ip] = [t for t in hits.get(ip, []) if time.time() - t < 3600] + [time.time()]
        n = int(self.headers.get('Content-Length', 0) or 0)
        if len(hits[ip]) > 20 or n > 20000:
            self.send_response(429); self.cors(); self.end_headers(); return
        try:
            p = json.loads(self.rfile.read(n))
            p = {k: (v[:500] if isinstance(v, str) else v) for k, v in p.items()}
            talent.log(test_in={k: p.get(k) for k in ('name', 'email', 'phone')}, assessment=p.get('assessment'))
            r = talent.on_test(p)
            code = 200
        except Exception as e:
            talent.log(err='intake', e=str(e)[:300]); r = {'ok': False}; code = 400
        self.send_response(code); self.cors(); self.send_header('Content-Type', 'application/json'); self.end_headers()
        self.wfile.write(json.dumps({'ok': bool(r and r.get('ok'))}).encode())
    def log_message(self, *a): pass

if __name__ == '__main__':
    ThreadingHTTPServer((talent.env.get('TALENT_INTAKE_HOST', '127.0.0.1'), int(talent.env.get('TALENT_INTAKE_PORT', '8788'))), H).serve_forever()
