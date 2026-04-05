from __future__ import annotations

import argparse, json, subprocess, sys, time, os
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"

DEFAULT_TESTS = [
    "tests/test_build.py", "tests/test_reference.py", "tests/test_radial_bands.py",
    "tests/test_material_profiles.py", "tests/test_local_volume_proxy.py", "tests/test_gravity.py",
    "tests/test_tissue.py", "tests/test_batch.py", "tests/test_calibration.py", "tests/test_static_settle.py",
    "tests/test_step10_settling.py", "tests/test_step11_settle_controller.py", "tests/test_step12_homeostasis.py",
]

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(); p.add_argument("--outdir", type=str, default="test_outputs"); return p.parse_args()

def main() -> None:
    args = parse_args(); outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    results=[]; md_lines=['# Step 12 test summary','']
    for test_path in DEFAULT_TESTS:
        label = test_path.replace('/', '__'); log_path = outdir / f'{label}.txt'; t0 = time.time()
        proc = subprocess.run([sys.executable, '-m', 'pytest', '-q', test_path], cwd=PROJECT_ROOT, capture_output=True, text=True, env={**os.environ, 'PYTHONPATH': str(SRC_DIR)})
        elapsed = time.time() - t0
        combined = (proc.stdout or '') + ('\n' if proc.stdout and proc.stderr else '') + (proc.stderr or '')
        log_path.write_text(combined, encoding='utf-8')
        status = 'PASS' if proc.returncode == 0 else 'FAIL'
        results.append({'test': test_path, 'status': status, 'elapsed_s': elapsed, 'log': str(log_path.relative_to(outdir.parent))})
        md_lines.append(f"- {status} `{test_path}` — {elapsed:.2f}s — log: `{log_path.name}`")
    overall = 'PASS' if all(r['status'] == 'PASS' for r in results) else 'FAIL'
    md_lines.extend(['', f'overall: {overall}'])
    (outdir / 'test_summary.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    (outdir / 'test_summary.md').write_text('\n'.join(md_lines)+'\n', encoding='utf-8')

if __name__ == '__main__':
    main()
