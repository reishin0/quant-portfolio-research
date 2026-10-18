"""Run one declared phase of early_warning_20261018 offline and write a dated receipt.

    python run_early_warning.py --phase development
    python run_early_warning.py --phase holdout

The development phase must be recorded before the holdout phase is run. The holdout phase
refuses to run without the development receipt, and neither phase changes any parameter.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from research.credit_funding import early_warning as ew

ROOT = Path(__file__).resolve().parent
RECEIPTS = ROOT / 'research/credit_funding'


def receipt_path(phase):
    return RECEIPTS / f'early_warning_{phase}_receipt_20261018.json'


def jsonable(frame):
    return json.loads(frame.replace({np.nan: None}).to_json(orient='records', date_format='iso'))


def tests(result, period):
    rows = []
    panel = result['panel']
    for sample in ['common', 'common_no_funding']:
        for s in ['P1', 'P2', 'B1', 'I0', 'I1', 'I2', 'F1', 'F2', 'E2']:
            obs, p = ew.permutation_p(panel, s, sample, period)
            rows.append(dict(sample=sample, signal=s, observed_precision=obs, permutation_p=p))
        for s in ['I1', 'E2', 'F2', 'I0', 'I2']:
            a, b = result['alarms'][(sample, s)], result['alarms'][(sample, 'P2')]
            lo, hi, n = ew.bootstrap_difference(a, b, list(panel))
            rows.append(dict(sample=sample, signal=s + '-P2', ci90_low_pp=lo, ci90_high_pp=hi, draws=n))
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=['development', 'holdout'], required=True)
    args = parser.parse_args()
    if receipt_path(args.phase).exists():
        raise SystemExit('Phase already recorded; a rerun needs a new declaration: ' + str(receipt_path(args.phase)))
    if args.phase == 'holdout' and not receipt_path('development').exists():
        raise SystemExit('Record the development phase first')
    inputs = ew.load(ROOT)
    result = ew.run_phase(inputs, args.phase)
    period = result['period']
    sig = tests(result, period)
    relative = []
    rpanel = ew.relative_panel(result['panel'])
    for mask in ['common', 'common_no_funding']:
        br, n = ew.base_rate(rpanel, mask, period)
        for s in ew.SIGNALS:
            r, _, _ = ew.evaluate(rpanel, s, mask, period)
            r.update(base_rate_pct=br, base_sessions=n, target='SPY_RELATIVE')
            relative.append(r)
    out = dict(phase=args.phase, executed_at=datetime.now(timezone.utc).isoformat(), period=period,
               manifest_sha256=hashlib.sha256((ROOT / ew.DATA_DIR / 'manifest.json').read_bytes()).hexdigest(),
               module_sha256=hashlib.sha256((ROOT / 'research/credit_funding/early_warning.py').read_bytes()).hexdigest(),
               coverage=jsonable(result['coverage']), results=jsonable(result['results']),
               relative_results=jsonable(pd.DataFrame(relative)), dependence_tests=jsonable(sig))
    receipt_path(args.phase).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    show = result['results']
    cols = ['signal', 'issuer_sessions', 'alarm_onsets', 'hits', 'false_alarms', 'same_day', 'in_episode',
            'precision_pct', 'episodes', 'warned', 'recall_pct', 'median_lead_sessions', 'false_per_250', 'base_rate_pct']
    with pd.option_context('display.width', 250, 'display.max_columns', 30):
        for mask in ['common', 'common_no_funding', 'own_price', 'own_issuer']:
            print('==', mask)
            print(show.loc[show['sample'].eq(mask), cols].round(2).to_string(index=False))
        print(sig.round(4).to_string(index=False))
    print('Receipt:', receipt_path(args.phase))


if __name__ == '__main__':
    main()
