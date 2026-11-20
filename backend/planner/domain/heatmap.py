"""Heatmap grid over the route corridor (D-14 to D-16, docs/03 §10)."""

import base64
import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import shapely

from .geo import EARTH_RADIUS_M, project_equirectangular
from .models import LatLon

FloatArray = npt.NDArray[np.float64]
BoolArray = npt.NDArray[np.bool_]

MIN_STEP_DEG = 0.08
FILL_FACTOR = 2.2  # roughly 45% of bbox cells fall inside a corridor
SIMPLIFY_M = 500.0
SCORE_SCALE = 50  # uint8 = floor(score * 50), 0..200
NO_DATA = 255
_M_PER_DEG = math.radians(1.0) * EARTH_RADIUS_M


@dataclass(frozen=True, slots=True)
class Grid:
    lat0: float  # centre of the south-west cell
    lon0: float
    dlat: float
    dlon: float
    rows: int
    cols: int

    def cell_centers(self) -> tuple[FloatArray, FloatArray]:
        """(rows, cols) arrays of cell-centre latitudes and longitudes."""
        lats = self.lat0 + np.arange(self.rows) * self.dlat
        lons = self.lon0 + np.arange(self.cols) * self.dlon
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        return lat_grid, lon_grid


def _corridor(
    routes: Sequence[Sequence[LatLon]], corridor_km: float, lat0: float
) -> shapely.Geometry:
    lines = []
    for coords in routes:
        xy = project_equirectangular(coords, lat0)
        lines.append(shapely.simplify(shapely.linestrings(xy), SIMPLIFY_M))
    return shapely.union_all(shapely.buffer(np.array(lines), corridor_km * 1000.0, quad_segs=4))


def _mask_for(corridor: shapely.Geometry, grid: Grid, lat0: float, pad_m: float) -> BoolArray:
    lat, lon = grid.cell_centers()
    x = lon * _M_PER_DEG * math.cos(math.radians(lat0))
    y = lat * _M_PER_DEG
    padded = shapely.buffer(corridor, pad_m, quad_segs=2)  # one ring of cells (D-16)
    mask: BoolArray = shapely.contains_xy(padded, x, y)
    return mask


def build_grid(
    routes: Sequence[Sequence[LatLon]], corridor_km: float, max_points: int
) -> tuple[Grid, BoolArray]:
    """Grid of `step`-degree cells covering the corridor, with at most `max_points` cells
    inside it. Returns the grid and a (rows, cols) mask of the cells to forecast."""
    all_pts = [p for r in routes for p in r]
    lat0 = sum(p.lat for p in all_pts) / len(all_pts)
    corridor = _corridor(routes, corridor_km, lat0)
    minx, miny, maxx, maxy = shapely.bounds(corridor)
    cos0 = math.cos(math.radians(lat0))
    lon_min, lon_max = minx / (_M_PER_DEG * cos0), maxx / (_M_PER_DEG * cos0)
    lat_min, lat_max = miny / _M_PER_DEG, maxy / _M_PER_DEG
    area_deg2 = (lon_max - lon_min) * (lat_max - lat_min)
    step = max(MIN_STEP_DEG, math.sqrt(area_deg2 / (max_points * FILL_FACTOR)))
    while True:
        grid = Grid(
            lat0=lat_min - step,
            lon0=lon_min - step,
            dlat=step,
            dlon=step,
            rows=math.ceil((lat_max - lat_min) / step) + 3,
            cols=math.ceil((lon_max - lon_min) / step) + 3,
        )
        mask = _mask_for(corridor, grid, lat0, step * _M_PER_DEG)
        if int(mask.sum()) <= max_points:
            return grid, mask
        step *= 1.15  # guarantee the budget


def encode_scores(scores: FloatArray, mask: BoolArray) -> bytes:
    """(hours, rows, cols) float scores -> uint8 bytes. NaN or unmasked -> 255."""
    valid = mask[np.newaxis, :, :] & ~np.isnan(scores)
    out = np.full(scores.shape, NO_DATA, dtype=np.uint8)
    # floor, not round: round() lifts the top of a band (e.g. 2.999 -> 150 -> 3.0) into the
    # next level, so the heatmap would disagree with the checkpoints (D-15).
    out[valid] = np.floor(np.clip(scores[valid], 0.0, 4.0) * SCORE_SCALE).astype(np.uint8)
    return out.tobytes()


def encode_mask(mask: BoolArray) -> bytes:
    """Row-major bitset, least significant bit first within each byte."""
    return np.packbits(mask.ravel().astype(np.uint8), bitorder="little").tobytes()


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")
