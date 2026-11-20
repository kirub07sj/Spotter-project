import { useRef } from 'react';
import type { Plan, RouteId } from '../../api/types';
import { useUi } from '../../store/ui';
import { RouteCard } from './RouteCard';

/** Route cards as a radiogroup: arrow keys move and select, Enter/Space select. */
export function RouteCards({ plan, selectedId }: { plan: Plan; selectedId: RouteId }) {
  const selectRoute = useUi((s) => s.selectRoute);
  const hoverRoute = useUi((s) => s.hoverRoute);
  const groupRef = useRef<HTMLDivElement>(null);
  const routes = plan.routes;

  const onKeyDown = (index: number) => (e: React.KeyboardEvent<HTMLDivElement>) => {
    const delta =
      e.key === 'ArrowDown' || e.key === 'ArrowRight'
        ? 1
        : e.key === 'ArrowUp' || e.key === 'ArrowLeft'
          ? -1
          : 0;
    if (delta !== 0) {
      e.preventDefault();
      const next = routes[(index + delta + routes.length) % routes.length];
      if (!next) return;
      selectRoute(next.id);
      groupRef.current?.querySelector<HTMLElement>(`[data-route-id="${next.id}"]`)?.focus();
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      selectRoute(routes[index]?.id ?? null);
    }
  };

  return (
    <div ref={groupRef} role="radiogroup" aria-label="Route options" className="space-y-2">
      {routes.map((route, i) => (
        <RouteCard
          key={route.id}
          route={route}
          selected={route.id === selectedId}
          focusable={route.id === selectedId}
          onSelect={() => selectRoute(route.id)}
          onHover={(h) => hoverRoute(h ? route.id : null)}
          onKeyDown={onKeyDown(i)}
        />
      ))}
    </div>
  );
}
