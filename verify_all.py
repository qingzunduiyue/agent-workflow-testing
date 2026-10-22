from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
EXPECTED={
    'test_07_blocked_api_exposes_guardrail_contract',
    'test_08_frontend_hook_preserves_blocked_state',
    'test_09_existing_memory_probe_targets_live_api_route',
}
reports={}
for variant in ['baseline','fixed']:
    completed=subprocess.run([sys.executable,'-B',str(ROOT/'run_checks.py'),variant],cwd=ROOT)
    expected_code=1 if variant=='baseline' else 0
    if completed.returncode!=expected_code:
        raise SystemExit(f'{variant}: unexpected process exit {completed.returncode}')
    data=json.loads((ROOT/f'{variant}_result.json').read_text(encoding='utf-8'))
    if data['errors'] or data['denied_external_network_attempts']:
        raise SystemExit(f'{variant}: infrastructure errors or attempted external networking')
    failed={entry['test'].split('.')[-1] for entry in data['tests'] if entry['status']=='failed'}
    if variant=='baseline' and failed!=EXPECTED:
        raise SystemExit(f'baseline: changed failure set {sorted(failed)}')
    if variant=='fixed' and (failed or data['passed']!=data['tests_run']):
        raise SystemExit('fixed: regression checks did not all pass')
    reports[variant]={k:data[k] for k in ['tests_run','passed','failed','errors']}
(ROOT/'verification-summary.json').write_text(json.dumps({'variants':reports,'verdict':'expected baseline failures and fixed regression pass','cloud_ci_status':'check the actual GitHub Actions run; this local result does not confirm cloud execution'},indent=2)+'\n',encoding='utf-8')
print('VERIFIED: expected baseline failures only; fixed regression passed')
