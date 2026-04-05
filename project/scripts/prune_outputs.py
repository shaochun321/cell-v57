from __future__ import annotations

import argparse
from pathlib import Path
import shutil

DEFAULT_KEEP = {
    'summary.json',
    'process_calculator_trace.json',
    'process_calculator_protocol_report.json',
    'process_calculator_analysis.json',
    'process_calculator_overview.png',
    'baseline_hardening_round3_analysis.json',
    'baseline_hardening_round3_overview.png',
    'baseline_hardening_round4_analysis.json',
    'baseline_hardening_round4_overview.png',
    'mirror_shell_interface_trace.json',
    'mirror_shell_interface_protocol_report.json',
    'mirror_shell_interface_analysis.json',
    'mirror_shell_interface_overview.png',
    'mirror_channel_atlas_trace.json',
    'mirror_channel_atlas_protocol_report.json',
    'mirror_channel_atlas_analysis.json',
    'mirror_channel_atlas_overview.png',
}

DELETE_SUFFIXES = {
    '.jsonl',
}
DELETE_FILENAMES = {
    'sensor_trace.json',
    'sensor_nodes.jsonl',
    'interface_trace.json',
    'interface_network_trace.json',
    'interface_lineage_trace.json',
    'interface_spectrum_trace.json',
    'interface_topology_trace.json',
    'interface_temporal_trace.json',
    'channel_hypergraph_trace.json',
    'channel_motif_trace.json',
    'metrics.png',
    'final_state.png',
}
DELETE_DIRS = {
    '__pycache__',
    '.pytest_cache',
    '.mplconfig',
    'tmp_round4_search',
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Prune regenerated outputs and cache files while keeping compact audit artifacts.')
    p.add_argument('--root', type=str, default='.')
    p.add_argument('--apply', action='store_true')
    return p.parse_args()


def collect_prunable_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for dirpath, dirnames, filenames in __import__('os').walk(root):
        current = Path(dirpath)
        for dirname in list(dirnames):
            if dirname in DELETE_DIRS:
                paths.append(current / dirname)
        for filename in filenames:
            path = current / filename
            if filename in DEFAULT_KEEP:
                continue
            if filename in DELETE_FILENAMES or path.suffix in DELETE_SUFFIXES:
                paths.append(path)
    return sorted(set(paths))


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    paths = collect_prunable_paths(root)
    total_bytes = 0
    for path in paths:
        if path.is_dir():
            total_bytes += sum(p.stat().st_size for p in path.rglob('*') if p.is_file())
        elif path.exists():
            total_bytes += path.stat().st_size
    print(f'候选删除项: {len(paths)}')
    print(f'预计释放: {total_bytes / (1024 * 1024):.2f} MB')
    for path in paths[:80]:
        print(path.relative_to(root))
    if len(paths) > 80:
        print(f'... 其余 {len(paths) - 80} 项省略')
    if not args.apply:
        print('未执行删除（预览模式）。加 --apply 执行。')
        return
    for path in reversed(paths):
        if not path.exists():
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    print('删除完成。')


if __name__ == '__main__':
    main()
