from __future__ import annotations

import argparse
import json
import os
import sys
from math import sqrt
from pathlib import Path
from statistics import mean
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / '.mplconfig'))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_stage1_scale_sign_audit import extract_features


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Tune hierarchical readout keys against the richer stress panel.')
    p.add_argument('--train-dir', type=str, default='outputs/stage1_scale_sign_audit_raw/N64')
    p.add_argument('--stress-dir', type=str, default='outputs/stage1_hierarchical_stress_panel_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_hierarchical_stress_tuned')
    p.add_argument('--translation-k', type=int, nargs='+', default=[2, 4, 6, 8, 12])
    p.add_argument('--nontranslation-k', type=int, nargs='+', default=[1, 2, 3, 4, 6])
    p.add_argument('--sign-k', type=int, nargs='+', default=[1, 2, 3, 4, 6, 8])
    return p.parse_args()


def semantic_label(case_name: str) -> str:
    if case_name.startswith('translation_x_pos'):
        return 'translation_x_pos'
    if case_name.startswith('translation_x_neg'):
        return 'translation_x_neg'
    if case_name.startswith('rotation_z_pos'):
        return 'rotation_z_pos'
    return 'baseline'


def load_panel(panel_dir: Path, semantic: bool) -> list[dict[str, Any]]:
    samples=[]
    for seed_dir in sorted(panel_dir.glob('seed_*')):
        seed=int(seed_dir.name.split('_')[1])
        for case_dir in sorted(seed_dir.iterdir()):
            if not case_dir.is_dir():
                continue
            if not (case_dir/'interface_trace.json').exists():
                continue
            label=semantic_label(case_dir.name) if semantic else case_dir.name
            samples.append({'seed':seed,'case_name':case_dir.name,'label':label,'features':extract_features(case_dir)})
    return samples


def zscore(samples, feature_names, means, stds):
    for s in samples:
        s['z_features']={k:(s['features'][k]-means[k])/stds[k] for k in feature_names}


def class_mean(samples, pred, keys):
    subset=[s for s in samples if pred(s)]
    return {k: mean([s['z_features'][k] for s in subset]) for k in keys}


def squared_distance(sample, center, keys):
    return sum((sample['z_features'][k]-center[k])**2 for k in keys)


def sign_spec(samples, keys):
    pos=class_mean(samples, lambda s: s['label']=='translation_x_pos', keys)
    neg=class_mean(samples, lambda s: s['label']=='translation_x_neg', keys)
    return {'mid':{k:0.5*(pos[k]+neg[k]) for k in keys}, 'weights':{k:pos[k]-neg[k] for k in keys}}


def sign_predict(sample, spec, keys):
    score=sum(spec['weights'][k]*(sample['z_features'][k]-spec['mid'][k]) for k in keys)
    return ('translation_x_pos' if score>0 else 'translation_x_neg'), score


def accuracy(preds):
    return sum(int(p['predicted']==p['label']) for p in preds)/len(preds) if preds else 0.0


def build_rankings(train, feature_names):
    trans=class_mean(train, lambda s: s['label'].startswith('translation'), feature_names)
    nontrans=class_mean(train, lambda s: not s['label'].startswith('translation'), feature_names)
    base=class_mean(train, lambda s: s['label']=='baseline', feature_names)
    rot=class_mean(train, lambda s: s['label']=='rotation_z_pos', feature_names)
    pos=class_mean(train, lambda s: s['label']=='translation_x_pos', feature_names)
    neg=class_mean(train, lambda s: s['label']=='translation_x_neg', feature_names)
    def rank(diff_a, diff_b=None):
        rows=[]
        for k in feature_names:
            score=abs(diff_a[k]) if diff_b is None else abs(diff_a[k])+0.25*abs(diff_b[k])
            rows.append({'feature':k,'score':score})
        rows.sort(key=lambda x:x['score'], reverse=True)
        return rows
    trans_diff={k:trans[k]-nontrans[k] for k in feature_names}
    nontrans_diff={k:base[k]-rot[k] for k in feature_names}
    sign_diff={k:pos[k]-neg[k] for k in feature_names}
    return {
        'translation': rank(trans_diff),
        'nontranslation': rank(nontrans_diff),
        'sign': rank(sign_diff),
    }


def eval_trial(train, panels, tg_keys, nt_keys, sign_keys):
    translation_center=class_mean(train, lambda s: s['label'].startswith('translation'), tg_keys)
    nontranslation_center=class_mean(train, lambda s: not s['label'].startswith('translation'), tg_keys)
    baseline_center=class_mean(train, lambda s: s['label']=='baseline', nt_keys)
    rotation_center=class_mean(train, lambda s: s['label']=='rotation_z_pos', nt_keys)
    spec=sign_spec([s for s in train if s['label'].startswith('translation')], sign_keys)
    results={}
    for scale, panel in panels.items():
        preds=[]
        for sample in panel:
            d_t=squared_distance(sample, translation_center, tg_keys)
            d_n=squared_distance(sample, nontranslation_center, tg_keys)
            if d_t < d_n:
                pred, score = sign_predict(sample, spec, sign_keys)
                preds.append({'label':sample['label'],'predicted':pred,'case_name':sample['case_name'],'stage1':'translation','sign_score':score})
            else:
                d_b=squared_distance(sample, baseline_center, nt_keys)
                d_r=squared_distance(sample, rotation_center, nt_keys)
                pred='baseline' if d_b<d_r else 'rotation_z_pos'
                preds.append({'label':sample['label'],'predicted':pred,'case_name':sample['case_name'],'stage1':'nontranslation'})
        tr=[p for p in preds if p['label'].startswith('translation')]
        results[scale]={'accuracy':accuracy(preds),'translation_accuracy':accuracy(tr),'predictions':preds}
    return results


def main():
    args=parse_args()
    outdir=Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    train=load_panel(Path(args.train_dir), semantic=False)
    feature_names=list(train[0]['features'].keys())
    means={k:mean([s['features'][k] for s in train]) for k in feature_names}
    stds={}
    for k in feature_names:
        var=mean([(s['features'][k]-means[k])**2 for s in train])
        stds[k]=sqrt(var) if var>0 else 1.0
    zscore(train, feature_names, means, stds)
    panels={
        'N64': load_panel(Path(args.stress_dir)/'N64', semantic=True),
        'N96': load_panel(Path(args.stress_dir)/'N96', semantic=True),
    }
    for p in panels.values():
        zscore(p, feature_names, means, stds)
    ranks=build_rankings(train, feature_names)

    trials=[]
    for kg in args.translation_k:
        tg=[r['feature'] for r in ranks['translation'][:kg]]
        for kn in args.nontranslation_k:
            nt=[r['feature'] for r in ranks['nontranslation'][:kn]]
            for ks in args.sign_k:
                sk=[r['feature'] for r in ranks['sign'][:ks]]
                res=eval_trial(train, panels, tg, nt, sk)
                score=0.25*res['N64']['accuracy']+0.25*res['N64']['translation_accuracy']+0.25*res['N96']['accuracy']+0.25*res['N96']['translation_accuracy']
                trials.append({
                    'translation_k':kg,'nontranslation_k':kn,'sign_k':ks,
                    'translation_keys':tg,'nontranslation_keys':nt,'sign_keys':sk,
                    'N64_accuracy':res['N64']['accuracy'],'N64_translation_accuracy':res['N64']['translation_accuracy'],
                    'N96_accuracy':res['N96']['accuracy'],'N96_translation_accuracy':res['N96']['translation_accuracy'],
                    'composite_score':score,
                    'results':res,
                })
    trials.sort(key=lambda x:(x['composite_score'], x['N96_accuracy'], x['N96_translation_accuracy']), reverse=True)
    best=trials[0]
    (outdir/'stage1_hierarchical_stress_tuned_analysis.json').write_text(json.dumps({'protocol':'stage1_hierarchical_stress_tuned','best_trial':best,'trials':trials[:30],'ranking_heads':{k:v[:20] for k,v in ranks.items()}}, ensure_ascii=False, indent=2))
    lines=['# Stage-1 hierarchical stress tuned audit','', 'Goal: retune the hierarchical external readout keys against the richer nuisance stress panel.','', '## Best trial','',
           f"- translation k: {best['translation_k']}", f"- nontranslation k: {best['nontranslation_k']}", f"- sign k: {best['sign_k']}",
           f"- N64 overall: {best['N64_accuracy']:.3f}", f"- N64 translation: {best['N64_translation_accuracy']:.3f}",
           f"- N96 overall: {best['N96_accuracy']:.3f}", f"- N96 translation: {best['N96_translation_accuracy']:.3f}", '', '### Translation keys']
    for k in best['translation_keys']: lines.append(f'- {k}')
    lines += ['', '### Nontranslation keys']
    for k in best['nontranslation_keys']: lines.append(f'- {k}')
    lines += ['', '### Sign keys']
    for k in best['sign_keys']: lines.append(f'- {k}')
    (outdir/'STAGE1_HIERARCHICAL_STRESS_TUNED_REPORT.md').write_text('\n'.join(lines))
    print(f'[OK] tuned stress audit written to {outdir}')

if __name__=='__main__':
    main()
