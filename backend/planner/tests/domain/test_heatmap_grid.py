import base64

import numpy as np
import pytest

from planner.domain.geo import haversine_m
from planner.domain.heatmap import (
    NO_DATA,
    SCORE_SCALE,
    build_grid,
    encode_mask,
    encode_scores,
)
from planner.domain.models import LatLon

DEN_SLC = [LatLon(39.74 + 0.01 * i, -104.99 - 0.069 * i) for i in range(101)]
SOUTH = [LatLon(39.74 - 0.008 * i, -104.99 - 0.069 * i) for i in range(101)]


def test_grid_respects_point_budget() -> None:
    for budget in (50, 200, 450):
        _, mask = build_grid([DEN_SLC, SOUTH], 40, budget)
        assert 0 < mask.sum() <= budget


def test_grid_covers_the_corridor_and_not_far_away() -> None:
    grid, mask = build_grid([DEN_SLC], 40, 450)
    lat, lon = grid.cell_centers()
    for p in DEN_SLC[::10]:
        r = round((p.lat - grid.lat0) / grid.dlat)
        c = round((p.lon - grid.lon0) / grid.dlon)
        assert mask[r, c], f"route point {p} is outside the mask"
    far = [
        (r, c)
        for r in range(grid.rows)
        for c in range(grid.cols)
        if mask[r, c]
        and min(haversine_m(LatLon(lat[r, c], lon[r, c]), p) for p in DEN_SLC)
        > 40_000 + 2 * 111_000 * grid.dlat
    ]
    assert far == []  # corridor plus one padding ring, nothing beyond


def test_grid_minimum_step_for_short_routes() -> None:
    short = [LatLon(39.74, -104.99), LatLon(39.80, -105.10)]
    grid, mask = build_grid([short], 40, 450)
    assert grid.dlat == pytest.approx(0.08) and grid.dlat == grid.dlon
    assert 0 < mask.sum() <= 450


def test_scores_encoding_round_trip() -> None:
    mask = np.array([[True, False], [True, True]])
    scores = np.array([[[0.0, 1.0], [np.nan, 4.0]], [[2.345, 3.0], [1.0, 3.99]]])
    raw = np.frombuffer(encode_scores(scores, mask), dtype=np.uint8).reshape(2, 2, 2)
    assert raw[0].tolist() == [[0, NO_DATA], [NO_DATA, 200]]
    assert raw[1].tolist() == [[117, NO_DATA], [50, 199]]  # floor(2.345*50), floor(3.99*50)


def test_encoding_keeps_floor_of_level_at_band_tops() -> None:
    # D-15: a score just under a band edge must not decode into the next level.
    tops = np.array([0.999, 1.999, 2.999, 3.999, 4.0, 0.0, 1.0])
    raw = np.frombuffer(encode_scores(tops.reshape(-1, 1, 1), np.array([[True]])), np.uint8)
    assert (np.floor(raw / SCORE_SCALE) == np.floor(tops)).all()


def test_mask_bitset_is_row_major_lsb_first() -> None:
    mask = np.zeros((3, 4), dtype=bool)
    mask[0, 0] = mask[0, 3] = mask[2, 1] = True  # flat indices 0, 3, 9
    data = encode_mask(mask)
    assert data == bytes([0b0000_1001, 0b0000_0010])
    assert base64.b64decode(base64.b64encode(data)) == data
