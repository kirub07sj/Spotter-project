import math

from planner.domain import units


def test_conversions_use_exact_factors() -> None:
    assert math.isclose(units.kmh_to_mph(1.609344), 1.0)
    assert math.isclose(units.mm_to_in(25.4), 1.0)
    assert math.isclose(units.cm_to_in(2.54), 1.0)
    assert math.isclose(units.m_to_mi(1609.344), 1.0)
    assert math.isclose(units.mi_to_m(1.0), 1609.344)
    assert math.isclose(units.lb_to_t(2204.62262), 1.0)
    assert math.isclose(units.mph_to_mps(1.0), 0.44704)


def test_typical_values() -> None:
    assert math.isclose(units.kmh_to_mph(88.5), 54.99, abs_tol=0.01)
    assert math.isclose(units.mm_to_in(2.54), 0.1)


def test_km_to_m() -> None:
    assert units.km_to_m(40) == 40_000
