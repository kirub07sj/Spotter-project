import polyline from '@mapbox/polyline';

export type LonLat = [number, number];

/** polyline6 -> [lon, lat] pairs, the order deck.gl and MapLibre expect. */
export function decodePolyline6(encoded: string): LonLat[] {
  return polyline.decode(encoded, 6).map(([lat, lon]) => [lon, lat] as LonLat);
}

export function boundsOf(paths: LonLat[][]): [[number, number], [number, number]] | null {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const path of paths) {
    for (const [x, y] of path) {
      if (x < minX) minX = x;
      if (y < minY) minY = y;
      if (x > maxX) maxX = x;
      if (y > maxY) maxY = y;
    }
  }
  return Number.isFinite(minX)
    ? [
        [minX, minY],
        [maxX, maxY],
      ]
    : null;
}
