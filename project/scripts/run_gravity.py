from __future__ import annotations

import argparse
from pathlib import Path
import sys
import os

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".mplconfig"))
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity



def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--num-cells", type=int, default=None)
    p.add_argument("--radius", type=float, default=None, help="固定球半径；不传则按 cell 数量自动估计")
    p.add_argument("--cell-radius", type=float, default=0.004)
    p.add_argument("--packing-fraction", type=float, default=0.68)
    p.add_argument("--radius-safety-factor", type=float, default=1.02)
    p.add_argument("--t-end", type=float, default=1.5)
    p.add_argument("--dt", type=float, default=5e-4)
    p.add_argument("--rng-seed", type=int, default=7)
    p.add_argument("--max-steps", type=int, default=None)
    p.add_argument("--outdir", type=str, default="outputs/gravity")
    p.add_argument("--disable-tissue", action="store_true")
    p.add_argument("--disable-foam-tissue", action="store_true")
    p.add_argument("--tissue-tension-k", type=float, default=18.0)
    p.add_argument("--tissue-pressure-k", type=float, default=900.0)
    p.add_argument("--tissue-radial-bands", type=int, default=4)
    p.add_argument("--tissue-local-pressure-k", type=float, default=90.0)
    p.add_argument("--tissue-shell-curvature-k", type=float, default=55.0)
    p.add_argument("--tissue-shell-radial-k", type=float, default=65.0)
    p.add_argument("--tissue-bulk-radial-k", type=float, default=14.0)
    p.add_argument("--tissue-band-interface-k", type=float, default=24.0)
    p.add_argument("--tissue-band-restoring-k", type=float, default=30.0)
    p.add_argument("--tissue-shell-reference-k", type=float, default=56.0)
    p.add_argument("--tissue-bulk-reference-k", type=float, default=8.0)
    p.add_argument("--tissue-inner-stiffness-scale", type=float, default=0.85)
    p.add_argument("--tissue-outer-stiffness-scale", type=float, default=1.35)
    p.add_argument("--tissue-inner-damping-scale", type=float, default=1.55)
    p.add_argument("--tissue-outer-damping-scale", type=float, default=0.90)
    p.add_argument("--tissue-inner-shear-scale", type=float, default=0.80)
    p.add_argument("--tissue-outer-shear-scale", type=float, default=1.45)
    p.add_argument("--tissue-band-damping-c", type=float, default=5.0)
    p.add_argument("--gravity-ramp-fraction", type=float, default=0.22)
    p.add_argument("--settle-damping-boost", type=float, default=3.0)
    p.add_argument("--settle-pressure-boost", type=float, default=1.40)
    p.add_argument("--settle-shell-boost", type=float, default=1.20)
    p.add_argument("--floor-tangential-c", type=float, default=6.0)
    p.add_argument("--floor-friction-mu", type=float, default=0.22)
    p.add_argument("--tissue-pressure-rate-damping-c", type=float, default=18.0)
    p.add_argument("--tissue-radial-rate-damping-c", type=float, default=3.0)
    p.add_argument("--tissue-shell-tangential-damping-c", type=float, default=2.0)
    p.add_argument("--disable-adaptive-settle", action="store_true")
    p.add_argument("--adaptive-settle-gain", type=float, default=0.12)
    p.add_argument("--adaptive-settle-max-boost", type=float, default=1.6)
    p.add_argument("--adaptive-settle-ke-ref", type=float, default=60.0)
    p.add_argument("--adaptive-settle-floor-ref", type=float, default=0.28)
    p.add_argument("--disable-settle-controller", action="store_true")
    p.add_argument("--settle-controller-activation-floor-contact", type=float, default=0.22)
    p.add_argument("--settle-controller-activation-time-fraction", type=float, default=0.32)
    p.add_argument("--settle-controller-gain", type=float, default=0.50)
    p.add_argument("--settle-controller-max-intensity", type=float, default=1.5)
    p.add_argument("--settle-controller-kinetic-per-cell-target", type=float, default=0.18)
    p.add_argument("--settle-controller-floor-gain", type=float, default=0.9)
    p.add_argument("--settle-controller-global-c", type=float, default=1.0)
    p.add_argument("--settle-controller-contact-c", type=float, default=4.5)
    p.add_argument("--settle-controller-radial-c", type=float, default=1.4)
    p.add_argument("--settle-controller-shell-tangential-c", type=float, default=0.9)
    p.add_argument("--disable-active-homeostasis", action="store_true")
    p.add_argument("--homeostasis-initial-energy", type=float, default=1.0)
    p.add_argument("--homeostasis-osmotic-force-k", type=float, default=14.0)
    p.add_argument("--homeostasis-contractile-force-k", type=float, default=0.0)
    p.add_argument("--homeostasis-recovery-force-k", type=float, default=12.0)
    p.add_argument("--homeostasis-osmotic-target-gain", type=float, default=1.10)
    p.add_argument("--homeostasis-contractile-target-gain", type=float, default=0.70)
    p.add_argument("--homeostasis-recovery-target-gain", type=float, default=0.90)
    p.add_argument("--homeostasis-activation-tau", type=float, default=0.08)
    p.add_argument("--homeostasis-energy-recovery-rate", type=float, default=0.11)
    p.add_argument("--homeostasis-energy-use-rate", type=float, default=0.18)
    p.add_argument("--homeostasis-energy-floor", type=float, default=0.08)
    p.add_argument("--homeostasis-max-energy", type=float, default=1.30)
    p.add_argument("--disable-homeostasis-gating", action="store_true")
    p.add_argument("--homeostasis-gate-on-threshold", type=float, default=0.12)
    p.add_argument("--homeostasis-gate-off-threshold", type=float, default=0.06)
    p.add_argument("--homeostasis-gate-tau-on", type=float, default=0.035)
    p.add_argument("--homeostasis-gate-tau-off", type=float, default=0.16)
    p.add_argument("--homeostasis-gate-compression-weight", type=float, default=1.0)
    p.add_argument("--homeostasis-gate-sag-weight", type=float, default=0.6)
    p.add_argument("--homeostasis-gate-rate-weight", type=float, default=0.25)
    p.add_argument("--homeostasis-stress-relax-tau", type=float, default=0.22)
    p.add_argument("--disable-sensor", action="store_true")
    p.add_argument("--record-every", type=int, default=20)
    p.add_argument("--sensor-record-every", type=int, default=20)
# 注意：这里我们统一使用 --disable-gravity
    p.add_argument("--disable-gravity", action="store_true", help="关闭重力和地板，实现悬浮")
    p.add_argument("--vestibular-motion", type=str, choices=["translation", "rotation"], default=None)
    p.add_argument("--vestibular-onset-fraction", type=float, default=0.4)
    p.add_argument("--vestibular-duration-fraction", type=float, default=1.0)
    p.add_argument("--vestibular-linear-accel", type=float, default=500.0)
    p.add_argument("--vestibular-linear-axis", type=str, choices=["x", "y", "z"], default="x")
    p.add_argument("--vestibular-linear-sign", type=float, default=-1.0)
    p.add_argument("--vestibular-angular-accel", type=float, default=3000.0)
    p.add_argument("--vestibular-rotation-axis", type=str, choices=["x", "y", "z"], default="z")
    p.add_argument("--vestibular-rotation-sign", type=float, default=1.0)
    return p.parse_args()



def get_num_cells(value: int | None) -> int:
    if value is not None:
        return value
    while True:
        raw = input("请输入细胞数量 num_cells: ").strip()
        try:
            x = int(raw)
            if x > 0:
                return x
        except ValueError:
            pass
        print("请输入一个正整数。")



def main() -> None:
    args = parse_args()
    num_cells = get_num_cells(args.num_cells)
    base_outdir = Path(args.outdir)
    if args.disable_gravity or args.vestibular_motion is not None:
        outdir = base_outdir
    else:
        outdir = base_outdir / f"gravity_N{num_cells}"
    cfg = GravityConfig(
        num_cells=num_cells,
        sphere_radius=args.radius,
        cell_radius=args.cell_radius,
        packing_fraction=args.packing_fraction,
        radius_safety_factor=args.radius_safety_factor,
        t_end=args.t_end,
        dt=args.dt,
        rng_seed=args.rng_seed,
        enable_tissue=not args.disable_tissue,
        enable_foam_tissue=not args.disable_foam_tissue,
        tissue_tension_k=args.tissue_tension_k,
        tissue_pressure_k=args.tissue_pressure_k,
        tissue_radial_bands=args.tissue_radial_bands,
        tissue_local_pressure_k=args.tissue_local_pressure_k,
        tissue_shell_curvature_k=args.tissue_shell_curvature_k,
        tissue_shell_radial_k=args.tissue_shell_radial_k,
        tissue_bulk_radial_k=args.tissue_bulk_radial_k,
        tissue_band_interface_k=args.tissue_band_interface_k,
        tissue_band_restoring_k=args.tissue_band_restoring_k,
        tissue_shell_reference_k=args.tissue_shell_reference_k,
        tissue_bulk_reference_k=args.tissue_bulk_reference_k,
        tissue_inner_stiffness_scale=args.tissue_inner_stiffness_scale,
        tissue_outer_stiffness_scale=args.tissue_outer_stiffness_scale,
        tissue_inner_damping_scale=args.tissue_inner_damping_scale,
        tissue_outer_damping_scale=args.tissue_outer_damping_scale,
        tissue_inner_shear_scale=args.tissue_inner_shear_scale,
        tissue_outer_shear_scale=args.tissue_outer_shear_scale,
        tissue_band_damping_c=args.tissue_band_damping_c,
        gravity_ramp_fraction=args.gravity_ramp_fraction,
        settle_damping_boost=args.settle_damping_boost,
        settle_pressure_boost=args.settle_pressure_boost,
        settle_shell_boost=args.settle_shell_boost,
        max_steps=args.max_steps,
        floor_tangential_c=args.floor_tangential_c,
        floor_friction_mu=args.floor_friction_mu,
        tissue_pressure_rate_damping_c=args.tissue_pressure_rate_damping_c,
        tissue_radial_rate_damping_c=args.tissue_radial_rate_damping_c,
        tissue_shell_tangential_damping_c=args.tissue_shell_tangential_damping_c,
        adaptive_settle_enabled=not args.disable_adaptive_settle,
        adaptive_settle_gain=args.adaptive_settle_gain,
        adaptive_settle_max_boost=args.adaptive_settle_max_boost,
        adaptive_settle_ke_ref=args.adaptive_settle_ke_ref,
        adaptive_settle_floor_ref=args.adaptive_settle_floor_ref,
        settle_controller_enabled=not args.disable_settle_controller,
        settle_controller_activation_floor_contact=args.settle_controller_activation_floor_contact,
        settle_controller_activation_time_fraction=args.settle_controller_activation_time_fraction,
        settle_controller_gain=args.settle_controller_gain,
        settle_controller_max_intensity=args.settle_controller_max_intensity,
        settle_controller_kinetic_per_cell_target=args.settle_controller_kinetic_per_cell_target,
        settle_controller_floor_gain=args.settle_controller_floor_gain,
        settle_controller_global_c=args.settle_controller_global_c,
        settle_controller_contact_c=args.settle_controller_contact_c,
        settle_controller_radial_c=args.settle_controller_radial_c,
        settle_controller_shell_tangential_c=args.settle_controller_shell_tangential_c,
        active_homeostasis_enabled=not args.disable_active_homeostasis,
        homeostasis_initial_energy=args.homeostasis_initial_energy,
        homeostasis_osmotic_force_k=args.homeostasis_osmotic_force_k,
        homeostasis_contractile_force_k=args.homeostasis_contractile_force_k,
        homeostasis_recovery_force_k=args.homeostasis_recovery_force_k,
        homeostasis_osmotic_target_gain=args.homeostasis_osmotic_target_gain,
        homeostasis_contractile_target_gain=args.homeostasis_contractile_target_gain,
        homeostasis_recovery_target_gain=args.homeostasis_recovery_target_gain,
        homeostasis_activation_tau=args.homeostasis_activation_tau,
        homeostasis_energy_recovery_rate=args.homeostasis_energy_recovery_rate,
        homeostasis_energy_use_rate=args.homeostasis_energy_use_rate,
        homeostasis_energy_floor=args.homeostasis_energy_floor,
        homeostasis_max_energy=args.homeostasis_max_energy,
        homeostasis_gating_enabled=not args.disable_homeostasis_gating,
        homeostasis_gate_on_threshold=args.homeostasis_gate_on_threshold,
        homeostasis_gate_off_threshold=args.homeostasis_gate_off_threshold,
        homeostasis_gate_tau_on=args.homeostasis_gate_tau_on,
        homeostasis_gate_tau_off=args.homeostasis_gate_tau_off,
        homeostasis_gate_compression_weight=args.homeostasis_gate_compression_weight,
        homeostasis_gate_sag_weight=args.homeostasis_gate_sag_weight,
        homeostasis_gate_rate_weight=args.homeostasis_gate_rate_weight,
        homeostasis_stress_relax_tau=args.homeostasis_stress_relax_tau,
        sensor_enabled=not args.disable_sensor,
        record_every=args.record_every,
        sensor_record_every=args.sensor_record_every,
        # === 新增：传入前庭配置 ===
# === 确保这里的 args.属性名 与上面 p.add_argument 里的字符串一致 ===
        disable_gravity=args.disable_gravity, 
        vestibular_motion=args.vestibular_motion,
        vestibular_onset_fraction=args.vestibular_onset_fraction,
        vestibular_duration_fraction=args.vestibular_duration_fraction,
        vestibular_linear_accel=args.vestibular_linear_accel,
        vestibular_linear_axis=args.vestibular_linear_axis,
        vestibular_linear_sign=args.vestibular_linear_sign,
        vestibular_angular_accel=args.vestibular_angular_accel,
        vestibular_rotation_axis=args.vestibular_rotation_axis,
        vestibular_rotation_sign=args.vestibular_rotation_sign,
    )
    result = run_gravity(cfg, outdir)
    print(f"输出目录: {outdir}")
    print(result.summary)


if __name__ == "__main__":
    main()
