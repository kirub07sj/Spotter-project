import type { RouteId } from '../api/types';

/** Route identity colours: deliberately unlike any risk colour (docs/04 §4). */
export const ROUTE_COLORS: Record<RouteId, { hex: string; rgb: [number, number, number] }> = {
  A: { hex: '#2563EB', rgb: [37, 99, 235] },
  B: { hex: '#0891B2', rgb: [8, 145, 178] },
  C: { hex: '#64748B', rgb: [100, 116, 139] },
};

export const ROUTE_BADGE: Record<RouteId, string> = {
  A: 'bg-route-a',
  B: 'bg-route-b',
  C: 'bg-route-c',
};
