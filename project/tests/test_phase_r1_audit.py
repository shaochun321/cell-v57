from __future__ import annotations

from pathlib import Path
import json

from cell_sphere_core.analysis.phase_r1 import summarize_phase_r1_audit


def test_phase_r1_audit_focuses_on_layered_rotation_repair():
    report_path = Path('outputs/phase_r1_sample/phase_r1_protocol_report.json')
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding='utf-8'))
    else:
        report = json.loads(Path('outputs/phase_r_sample/phase_r_protocol_report.json').read_text(encoding='utf-8'))
    audit = summarize_phase_r1_audit(report)
    focused = audit['focused_metrics']
    status = audit['repair_status']
    assert focused['layered_rotation_score'] >= 0.85
    assert focused['layered_advantage_vs_discrete'] > 0.0
    assert focused['rotation_consistency_mean'] >= 0.80
    assert status['layered_best_rotation_track'] is True
