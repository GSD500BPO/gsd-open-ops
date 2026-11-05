"""Offline smoke test: no network, no models, TALENT_LIVE=0. Run: python3 tests/test_offline.py
Copies the code into a temp dir so the real state.json / events.jsonl are never touched."""
import json, os, shutil, subprocess, sys, tempfile

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tmp = tempfile.mkdtemp(prefix='ramon-test-')
for f in os.listdir(SRC):
    p = os.path.join(SRC, f)
    if f.endswith(('.py', '.html')): shutil.copy(p, tmp)
shutil.copytree(os.path.join(SRC, 'scenarios'), os.path.join(tmp, 'scenarios'))
open(os.path.join(tmp, '.env'), 'w').write('TALENT_LIVE=0\nTALENT_COMPANY=Acme BPO\nTALENT_DEFAULT_COUNTRY_CODE=57\n'
                                           'TALENT_RATE_LADDER=90:3,80:2,0:1\nTALENT_SPEECH=1\nTALENT_REEL_SALT=test-salt\n')
os.environ.pop('TALENT_ENV_FILE', None)
sys.path.insert(0, tmp); os.chdir(tmp)
import talent, roleplay  # noqa: E402

ok = 0
def check(cond, what):
    global ok
    assert cond, what; ok += 1

check(not talent.LIVE, 'dry by default')
check(talent.norm('300 123 4567') == '573001234567', 'local mobile gets country code')
check(talent.norm('+1 (555) 000-0000') == '15550000000', 'international number kept')
check(talent.rate_for({'composite': 95}) == 3 and talent.rate_for({'composite': 85}) == 2 and talent.rate_for({'composite': 10}) == 1, 'rate ladder')
check(len(talent.reel_key('15550000000')) == 20, 'reel key')
pts, got, q, w = roleplay.grade(0, "Hi, this is Ana calling about the free water test you requested. Do you have a quick minute? "
                                   "Are you on city water or a well, and do you notice any taste or smell?")
check(pts >= 15, f'water roleplay round 1 graded ({pts}, {got})')

# full dry flow: site test result + video -> speech done -> passed
k = talent.intake({'name': 'Test Candidate', 'phone': '15550000001', 'email': 'test@example.com', 'source': 'site'})
check(k == '15550000001', 'intake')
with talent.State() as d:
    d['c'][k].update(video_path='recruiting/x/v.mp4', speech_status='done', speech={'overall_0_100': 82, 'speaking_cefr': 'B2'})
r = talent.on_test({'phone': k, 'assessment': {'composite_score': 80, 'english_score': 90, 'sales_score': 70, 'typing_wpm': 45}})
check(r.get('stage') == 'passed', f'passes: {r}')
k2 = talent.intake({'name': 'Low Speaker', 'phone': '15550000002', 'source': 'site'})
with talent.State() as d:
    d['c'][k2].update(video_path='v.mp4', speech_status='done', speech={'overall_0_100': 40})
check(talent.on_test({'phone': k2, 'assessment': {'composite_score': 80, 'english_score': 90}}).get('stage') == 'failed', 'speaking gate')
events = [json.loads(l) for l in open('events.jsonl')]
check(any(e.get('dry') for e in events) and not any(e.get('sent') for e in events), 'nothing sent while dry')
print(f'OK {ok} checks'); shutil.rmtree(tmp)
