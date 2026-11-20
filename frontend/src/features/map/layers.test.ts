import { renderHook } from '@testing-library/react';
import { planNoSafe } from '../../test/plans';
import { prepareRouteLayers, routeLayers, type LayerState } from './layers';
import { useMapData } from './useMapData';

const state: LayerState = {
  selectedId: 'A',
  hoveredRouteId: null,
  hoveredCheckpoint: null,
  emphasizedCheckpoint: 0,
  showAllRoutes: true,
  showCheckpoints: true,
  beforeId: undefined,
};

it('keeps route and checkpoint buffers stable when the forecast advances', () => {
  const { result } = renderHook(() => useMapData(planNoSafe));
  if (!result.current) throw new Error('Missing map fixture');
  const data = prepareRouteLayers(result.current, 'A', true, true);
  const first = routeLayers(data, state);
  const later = routeLayers(data, { ...state, emphasizedCheckpoint: 1 });
  expect(first.length).toBeGreaterThan(0);
  for (const layer of first) {
    expect(later.find((next) => next.id === layer.id)?.props.data).toBe(layer.props.data);
  }
});

it('adds dashed outlines only to low-confidence checkpoints', () => {
  const { result } = renderHook(() => useMapData(planNoSafe));
  if (!result.current) throw new Error('Missing map fixture');
  const data = result.current;
  const cp = data.checkpoints.A?.[0];
  if (!cp) throw new Error('Missing checkpoint');
  data.checkpoints.A = [
    { ...cp, low_confidence: true },
    { ...cp, low_confidence: false },
  ];
  const prepared = prepareRouteLayers(data, 'A', true, true);
  expect(prepared.confidence).toHaveLength(1);
  expect(routeLayers(prepared, state).some((layer) => layer.id === 'checkpoint-confidence')).toBe(
    true,
  );
  expect(prepareRouteLayers(data, 'A', true, false).confidence).toHaveLength(0);
});
