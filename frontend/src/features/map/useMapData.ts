import { useMemo } from 'react';
import type { Checkpoint, Plan, RiskLevel, RouteId } from '../../api/types';
import { boundsOf, decodePolyline6, type LonLat } from '../../lib/polyline';

export interface MapRoute {
  id: RouteId;
  label: string;
  path: LonLat[];
  cumTimeS: number[];
  durationS: number;
}

export interface MapSegment {
  routeId: RouteId;
  level: RiskLevel;
  fromMi: number;
  toMi: number;
  path: LonLat[];
}

export interface MapData {
  planId: string;
  routes: MapRoute[];
  segments: MapSegment[];
  checkpoints: Record<string, Checkpoint[]>;
  /** checkpoint ETAs as seconds after departure, per route */
  checkpointOffsetsS: Record<string, number[]>;
  endpoints: { kind: 'origin' | 'destination'; position: LonLat }[];
  bounds: [[number, number], [number, number]] | null;
}

/** Decodes every polyline once per plan (keyed by plan_id), never per render or per frame. */
export function useMapData(plan: Plan | undefined): MapData | null {
  const planId = plan?.plan_id;
  return useMemo(() => {
    if (!plan) return null;
    const routes = plan.routes.map((r) => ({
      id: r.id,
      label: r.label,
      path: decodePolyline6(r.geometry),
      cumTimeS: r.cum_time_s,
      durationS: r.duration_s,
    }));
    const segments = plan.routes.flatMap((r) =>
      r.risk_segments.map((s) => ({
        routeId: r.id,
        level: s.level,
        fromMi: s.from_mi,
        toMi: s.to_mi,
        path: decodePolyline6(s.geometry),
      })),
    );
    const checkpoints = Object.fromEntries(plan.routes.map((r) => [r.id, r.checkpoints]));
    const t0 = new Date(plan.assumptions.departure_time).getTime();
    const checkpointOffsetsS = Object.fromEntries(
      plan.routes.map((r) => [
        r.id,
        r.checkpoints.map((c) => (new Date(c.eta).getTime() - t0) / 1000),
      ]),
    );
    const first = routes[0]?.path;
    const endpoints = first?.length
      ? [
          { kind: 'origin' as const, position: first[0] as LonLat },
          { kind: 'destination' as const, position: first[first.length - 1] as LonLat },
        ]
      : [];
    return {
      planId: plan.plan_id,
      routes,
      segments,
      checkpoints,
      checkpointOffsetsS,
      endpoints,
      bounds: boundsOf(routes.map((r) => r.path)),
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- keyed by plan_id on purpose
  }, [planId]);
}
