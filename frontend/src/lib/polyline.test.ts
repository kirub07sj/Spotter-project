import polyline from '@mapbox/polyline';
import { boundsOf, decodePolyline6 } from './polyline';

describe('polyline6', () => {
  it('decodes to [lon, lat] pairs', () => {
    const encoded = polyline.encode(
      [
        [39.7392, -104.9903],
        [40.7608, -111.891],
      ],
      6,
    );
    expect(decodePolyline6(encoded)).toEqual([
      [-104.9903, 39.7392],
      [-111.891, 40.7608],
    ]);
  });

  it('computes bounds', () => {
    expect(
      boundsOf([
        [
          [-105, 39],
          [-111, 41],
        ],
        [[-108, 38]],
      ]),
    ).toEqual([
      [-111, 38],
      [-105, 41],
    ]);
    expect(boundsOf([])).toBeNull();
  });
});
