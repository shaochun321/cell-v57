
#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from cell_sphere_core.analysis.process_summary_translation_x_pos_m2_4_material_baseline_recheck_audit import (
    build_m2_4_material_baseline_recheck,
)

def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    out_dir = repo_root / "outputs" / "m2_4_material_baseline_recheck_audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    audit = build_m2_4_material_baseline_recheck(repo_root)
    out_path = out_dir / "process_summary_translation_x_pos_m2_4_material_baseline_recheck_audit.json"
    out_path.write_text(json.dumps(audit, indent=2))
    print(out_path)

if __name__ == "__main__":
    main()
