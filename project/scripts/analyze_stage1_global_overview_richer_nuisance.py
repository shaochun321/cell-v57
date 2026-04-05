from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from statistics import mean
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / '.mplconfig'))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_DIR = PROJECT_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cell_sphere_core.analysis.global_overview import extract_overview_features
from scripts.analyze_stage1_global_overview_candidate import GATE_KEYS, NONTRANSLATION_KEYS, SIGN_KEYS, evaluate
from scripts.analyze_stage1_global_overview_audit import semantic_label, zscore


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Apply the fixed global overview candidate to N160 richer nuisance.')
    p.add_argument('--seen-root', type=str, default='outputs/stage1_global_overview_panel_raw')
    p.add_argument('--n160-root', type=str, default='outputs/stage1_n160_richer_nuisance_panel_raw/N160')
    p.add_argument('--outdir', type=str, default='outputs/stage1_global_overview_richer_nuisance')
    p.add_argument('--seen-scales', type=int, nargs='+', default=[64,96,128])
    return p.parse_args()


def load_panel(panel_dir: Path) -> list[dict[str, Any]]:
    samples=[]
    scale = int(panel_dir.name[1:]) if panel_dir.name.startswith('N') else 160
    for seed_dir in sorted(panel_dir.glob('seed_*')):
        seed=int(seed_dir.name.split('_')[1])
        for case_dir in sorted(seed_dir.iterdir()):
            if not case_dir.is_dir():
                continue
            samples.append({
                'scale': scale,
                'seed': seed,
                'case_name': case_dir.name,
                'label': semantic_label(case_dir.name),
                'features': extract_overview_features(case_dir),
            })
    return samples


def accuracy(rows: list[dict[str, Any]]) -> float:
    return sum(int(r['predicted']==r['label']) for r in rows)/len(rows) if rows else 0.0


def main() -> None:
    args=parse_args()
    outdir=Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    seen=[]
    for scale in args.seen_scales:
        seen.extend(load_panel(Path(args.seen_root)/f'N{scale}'))
    target=load_panel(Path(args.n160_root))
    all_samples=seen+target
    feature_names=list(seen[0]['features'].keys())
    means={k:mean([s['features'][k] for s in seen]) for k in feature_names}
    stds={}
    for k in feature_names:
        var=mean([(s['features'][k]-means[k])**2 for s in seen])
        stds[k]=math.sqrt(var) if var>0 else 1.0
    zscore(all_samples, feature_names, means, stds)
    result=evaluate(seen,target)
    payload={
        'protocol':'stage1_global_overview_richer_nuisance',
        'seen_scales':args.seen_scales,
        'gate_keys':GATE_KEYS,
        'nontranslation_keys':NONTRANSLATION_KEYS,
        'sign_keys':SIGN_KEYS,
        'result':result,
    }
    (outdir/'stage1_global_overview_richer_nuisance_analysis.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2))
    lines=[
        '# Stage-1 global overview candidate on N160 richer nuisance',
        '',
        'This applies the fixed, physically interpretable overview candidate (selected without using N160 target labels) to the richer nuisance N160 panel.',
        '',
        f"- overall: {result['accuracy']:.3f}",
        f"- translation: {result['translation_accuracy']:.3f}",
        '',
        f"- gate keys: {', '.join(GATE_KEYS)}",
        f"- nontranslation keys: {', '.join(NONTRANSLATION_KEYS)}",
        f"- sign keys: {', '.join(SIGN_KEYS)}",
        '',
    ]
    (outdir/'STAGE1_GLOBAL_OVERVIEW_RICHER_NUISANCE_REPORT.md').write_text('\n'.join(lines))
    print(f'[OK] wrote overview richer nuisance audit to {outdir}')

if __name__=='__main__':
    main()
