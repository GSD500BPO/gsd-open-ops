"""Minimal Zoho Cliq client for the team channel: post(channel_unique_name, {'text': ..., 'card': {...}}).

OAuth (Zoho API console -> Self Client), scope ZohoCliq.Webhooks.CREATE:
  CLIQ_CLIENT_ID, CLIQ_CLIENT_SECRET, CLIQ_REFRESH_TOKEN   (falls back to ZOHO_CLIENT_ID / ZOHO_CLIENT_SECRET)
  ZOHO_ACCOUNTS_URL (default https://accounts.zoho.com; use .eu / .in etc. for other data centers)
  CLIQ_API_URL      (default https://cliq.zoho.com)"""
import json, time, urllib.request, urllib.parse, urllib.error

_tok = {'t': None, 'exp': 0}


def _env():
    import talent
    return talent.env


def token():
    if _tok['t'] and time.time() < _tok['exp']: return _tok['t']
    e = _env()
    q = urllib.parse.urlencode({'grant_type': 'refresh_token',
                                'client_id': e.get('CLIQ_CLIENT_ID') or e['ZOHO_CLIENT_ID'],
                                'client_secret': e.get('CLIQ_CLIENT_SECRET') or e['ZOHO_CLIENT_SECRET'],
                                'refresh_token': e['CLIQ_REFRESH_TOKEN']}).encode()
    d = json.load(urllib.request.urlopen(e.get('ZOHO_ACCOUNTS_URL', 'https://accounts.zoho.com') + '/oauth/v2/token', q, timeout=30))
    _tok.update(t=d['access_token'], exp=time.time() + 3000)
    return _tok['t']


def post(channel, msg):
    url = _env().get('CLIQ_API_URL', 'https://cliq.zoho.com') + f'/api/v2/channelsbyname/{channel}/message'
    req = urllib.request.Request(url, method='POST', data=json.dumps(msg).encode(),
                                 headers={'Authorization': 'Zoho-oauthtoken ' + token(), 'Content-Type': 'application/json'})
    try:
        b = urllib.request.urlopen(req, timeout=40).read()
        return json.loads(b) if b.strip() else {'ok': True}
    except urllib.error.HTTPError as e:
        return {'_err': e.code, '_body': e.read()[:300].decode('utf-8', 'replace')}
