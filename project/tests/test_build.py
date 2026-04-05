from pathlib import Path
import json
import subprocess
import sys


def test_build_sphere_smoke(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    outdir = tmp_path / "out"
    cmd = [
        sys.executable,
        str(project_root / "scripts" / "build_sphere.py"),
        "--num-cells", "200",
        "--outdir", str(outdir),
    ]
    proc = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr

    summary_path = outdir / "sphere_N200" / "summary.json"
    img_path = outdir / "sphere_N200" / "aggregate.png"
    assert summary_path.exists()
    assert img_path.exists()

    data = json.loads(summary_path.read_text(encoding="utf-8"))
    assert data["num_cells"] == 200
    assert data["num_edges"] > 0
