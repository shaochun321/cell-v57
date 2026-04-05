from __future__ import annotations

from typing import Iterable


def assert_margin(value: float, *, eps: float = 1e-3, label: str = 'margin') -> None:
    assert value > eps, f'Expected {label} > {eps}, got {value!r}'


def assert_sign_flip(first: float, second: float, *, min_abs: float = 1e-3, min_sep: float = 1e-3, label: str = 'signal') -> None:
    assert max(abs(first), abs(second)) > min_abs, f'Expected at least one {label} magnitude > {min_abs}, got {first!r}, {second!r}'
    assert first * second < 0.0, f'Expected {label} to flip sign, got {first!r}, {second!r}'
    assert abs(first - second) > min_sep, f'Expected {label} separation > {min_sep}, got {abs(first-second)!r}'


def assert_fraction(value: float, *, floor: float, label: str = 'fraction') -> None:
    assert 0.0 <= value <= 1.0, f'Expected {label} in [0, 1], got {value!r}'
    assert value >= floor, f'Expected {label} >= {floor}, got {value!r}'


def assert_flip_or_one_sided(first: float, second: float, *, min_abs: float = 1e-3, near_zero: float = 2e-3, min_sep: float = 1e-3, label: str = 'signal') -> None:
    assert max(abs(first), abs(second)) > min_abs, f'Expected at least one {label} magnitude > {min_abs}, got {first!r}, {second!r}'
    same_sign = first * second >= 0.0
    if same_sign:
        assert min(abs(first), abs(second)) < near_zero, f'Expected {label} to flip or one side to be near zero (< {near_zero}), got {first!r}, {second!r}'
    assert abs(first - second) > min_sep, f'Expected {label} separation > {min_sep}, got {abs(first-second)!r}'


def assert_required_keys(payload: dict, required: Iterable[str], *, label: str = 'payload') -> None:
    missing = [key for key in required if key not in payload]
    assert not missing, f'Expected {label} to contain keys {missing!r}'


def assert_phase_coverage(phase_counts: dict[str, int], required: Iterable[str], *, label: str = 'phase_counts') -> None:
    missing = [phase for phase in required if phase not in phase_counts]
    assert not missing, f'Expected {label} to contain phases {missing!r}, got {phase_counts!r}'


def assert_case_mode(case_payload: dict, *, expected_overall: str | None = None, expected_active: str | None = None, label: str = 'case') -> None:
    if expected_overall is not None:
        got = str(case_payload.get('dominant_mode', 'none'))
        assert got == expected_overall, f'Expected {label} dominant_mode == {expected_overall!r}, got {got!r}'
    if expected_active is not None:
        got = str(case_payload.get('active_dominant_mode', 'none'))
        assert got == expected_active, f'Expected {label} active_dominant_mode == {expected_active!r}, got {got!r}'
