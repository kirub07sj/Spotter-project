"""Golden scenarios (docs/03 §9). Each route is 100 mi with checkpoints every 25 mi, so the
checkpoints own 12.5, 25, 25, 25 and 12.5 miles (D-09). Weather per checkpoint, expected
winner, order and reasons are all written by hand. Never regenerate them from the code.

The same scenarios run end to end through the plan service in planner/tests/api."""

from planner.tests.golden import GOLDEN_SCENARIOS, GoldenScenario, run_domain_pipeline


def check(scenario: GoldenScenario) -> None:
    result = run_domain_pipeline(scenario)
    assert result.recommendation.route_id == scenario.expected_winner
    assert result.recommendation.status == scenario.expected_status
    assert result.order == scenario.expected_order
    assert result.recommendation.reasons == scenario.expected_reasons


def test_1_severe_miles_decide() -> None:
    check(GOLDEN_SCENARIOS["severe_decides"])


def test_2_severe_tied_high_decides() -> None:
    check(GOLDEN_SCENARIOS["high_decides"])


def test_3_severe_and_high_tied_average_risk_decides() -> None:
    check(GOLDEN_SCENARIOS["avg_risk_decides"])


def test_4_everything_tied_duration_decides() -> None:
    check(GOLDEN_SCENARIOS["duration_decides"])


def test_5_every_route_has_no_travel() -> None:
    check(GOLDEN_SCENARIOS["no_safe_route"])


def test_6_load_rule_flips_the_winner_light_load() -> None:
    check(GOLDEN_SCENARIOS["load_flip_35k"])


def test_6_load_rule_flips_the_winner_heavy_load() -> None:
    scenario = GOLDEN_SCENARIOS["load_flip_45k"]
    check(scenario)
    # The flip is caused by the load rule on route A's mile-50 checkpoint.
    result = run_domain_pipeline(scenario)
    assert result.load_adjusted["A"] == [False, False, True, False, False]


def test_scenarios_differ_only_by_load() -> None:
    light, heavy = GOLDEN_SCENARIOS["load_flip_35k"], GOLDEN_SCENARIOS["load_flip_45k"]
    assert light.routes == heavy.routes
    assert (light.load_lb, heavy.load_lb) == (35_000, 45_000)
