from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity


def test_static_settle_diagnostics_present():
    result = run_gravity(
        GravityConfig(
            num_cells=48,
            t_end=0.03,
            dt=0.001,
            gravity_ramp_fraction=0.2,
            settle_damping_boost=2.2,
            settle_pressure_boost=1.2,
            settle_shell_boost=1.1,
        ),
        save_outputs=False,
    )
    summary = result.summary
    assert 'equilibrium_diagnostics' in summary
    assert 'settling_schedule' in summary
    assert 'tail_kinetic_mean' in summary['equilibrium_diagnostics']
    assert 'tail_sag_mean' in summary['equilibrium_diagnostics']
    assert summary['settling_schedule']['gravity_ramp_fraction'] == 0.2
    assert 'adaptive_settle_enabled' in summary['settling_schedule']
    assert 'adaptive_settle_max_boost' in summary['simulator_status']
    assert 'pressure_rate_ratio' in summary
