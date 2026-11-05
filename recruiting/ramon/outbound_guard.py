"""Outbound guard: the last line of defense against message loops.

Every automated email goes through allow(): a per-recipient, per-channel daily cap, persisted to disk, plus kill switches.
We learned this the hard way: a retry bug once re-sent the same email dozens of times to the same people. Caps and
idempotency markers (save state BEFORE sending) make that impossible.

Kill switches (touch a file to stop everything, delete it to resume):
  <dir>/PAUSE_ALL          stops every sender that uses this guard
  <dir>/PAUSE_<name>       stops one sender (e.g. PAUSE_hire_alert)
<dir> = OUTBOUND_GUARD_DIR (default ./guard next to this file)."""
import fcntl, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.environ.get('OUTBOUND_GUARD_DIR', os.path.join(HERE, 'guard'))
DEFAULT_CAP = int(os.environ.get('OUTBOUND_GUARD_DAILY_CAP', '3'))   # automated messages per recipient per channel per day


def paused(name=''):
    return os.path.exists(os.path.join(DIR, 'PAUSE_ALL')) or (name and os.path.exists(os.path.join(DIR, 'PAUSE_' + name)))


def assert_not_paused(name):
    if paused(name):
        print(f'outbound_guard: {name} is paused', file=sys.stderr); sys.exit(0)


def allow(recipient, channel, sender, cap=None, note=''):
    """Reserve one send slot. Returns False (and sends nothing) when paused or over the cap."""
    if paused(sender): return False
    os.makedirs(DIR, exist_ok=True)
    f = os.path.join(DIR, 'ledger.json'); day = time.strftime('%Y-%m-%d')
    with open(f + '.lock', 'w') as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        led = json.load(open(f)) if os.path.exists(f) else {}
        if led.get('day') != day: led = {'day': day, 'n': {}}
        key = f'{channel}:{(recipient or "").strip().lower()}'
        n = led['n'].get(key, 0)
        if n >= (cap or DEFAULT_CAP): return False
        led['n'][key] = n + 1
        tmp = f + '.tmp'; json.dump(led, open(tmp, 'w')); os.replace(tmp, f)
    return True
