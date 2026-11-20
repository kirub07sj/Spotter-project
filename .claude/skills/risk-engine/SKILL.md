---
name: risk-engine
description: Use when implementing or changing checkpoint sampling, ETA calculation, weather bucket lookup, risk classification, load rules, mile attribution, route ranking or recommendation reasons in backend/planner/domain.
---

# Risk Engine

This is the 40% "logic" part of the grade. Correctness beats cleverness.

## Before you start
1. Read `docs/01-SPEC.md` section 2 (decisions D-01 to D-13) and `docs/03-ALGORITHMS.md` sections 4 to 9.
2. Find the decision ID that covers your change. If there isn't one, stop and propose a decision (AGENTS.md rule 2).

## Files
| File | Owns |
|---|---|
| `domain/levels.py` | `Level` enum and **every threshold constant**. The only place numbers live |
| `domain/eta.py` | speed cap, cumulative arrays |
| `domain/sampling.py` | checkpoint miles, `locate()` |
| `domain/weather_lookup.py` | hour bucket selection (D-08) |
| `domain/risk.py` | `classify_wind/rain/snow`, `classify_checkpoint`, `continuous_score` (scalar + numpy) |
| `domain/attribution.py` | owned intervals, `RouteStats`, risk segments |
| `domain/ranking.py` | `ranking_key`, `recommend`, `explain` |

## Hard rules
- Pure functions only. No Django, no httpx, no `datetime.now()`.
- Band edges: inclusive lower bound. Rain and snow No Travel is strictly `>`. Wind No Travel is `>=` 55 (D-01).
- Load rules change the **wind** level only. Load comparisons are strict `>` (D-03).
- Overall = max of the components. Record `dominant_factor` and `load_adjusted`.
- Unknown weather gives `Level.UNKNOWN`, which is excluded from stats and raises a warning. Never default to LOW.
- Ranking key order: No Travel miles, Severe miles, High miles, average risk, minutes, then id (D-11). Round before comparing.
- Scalar and vectorized `continuous_score` must agree (test with 10k random samples).

## Workflow
1. **Write the tests first.** Add rows to the boundary table in `tests/domain/test_risk_boundaries.py`. Import thresholds from `levels.py`, never retype the numbers.
2. Implement the smallest change that makes them pass.
3. Run the property tests (`test_risk_properties.py`): monotonic in each input and in load, overall >= components.
4. Run the golden scenarios (`test_golden_scenarios.py`). If an expected winner changes, that's a behaviour change: update the spec first and explain it in the commit.
5. `uv run pytest planner/tests/domain -q && uv run mypy planner/domain`.

## Boundary values every change must keep passing
Wind: 24.99, 25, 34.99, 35, 44.99, 45, 54.99, 55. Loads: 30,000 / 30,001 / 40,000 / 40,001.
Rain: 0.0999, 0.10, 0.2499, 0.25, 0.4999, 0.50, 1.00, 1.0001.
Snow: 0.49, 0.5, 0.99, 1.0, 1.99, 2.0, 3.0, 3.01.

## Reasons text
`explain(best, other)` describes the **first** key position where they differ, in plain words with numbers. Examples are in `03-ALGORITHMS.md` section 9. Keep the wording short. It's shown in the banner.

## Common mistakes
- Using `precipitation` as rain (counts snow twice, D-05).
- Using the floor hour for the bucket (D-08 says ceil, because values cover the preceding hour).
- Giving each stretch the max of its two end checkpoints (D-09 says midpoint split).
- Comparing raw floats in ranking, so 0.30000000004 beats 0.3.
