import { QueryClientProvider } from '@tanstack/react-query';
import { lazy, Suspense } from 'react';
import { usePlan } from './api/hooks';
import { AssumptionsFooter } from './app/AssumptionsFooter';
import { queryClient } from './app/queryClient';
import { ResultsPanel } from './app/ResultsPanel';
import { ForecastSlider, HeatmapController } from './features/heatmap';
import { PlanForm } from './features/plan-form';
import { useUi } from './store/ui';

// MapLibre + deck.gl live in their own chunk so the form is interactive first (docs/04 §7).
const MapView = lazy(() => import('./features/map/MapView').then((m) => ({ default: m.MapView })));

function MapFallback() {
  return <div className="h-full w-full bg-[#e9eef2]" aria-label="Loading map" />;
}

function Shell() {
  const submitted = useUi((s) => s.submitted);
  const submit = useUi((s) => s.submit);
  const selectedId = useUi((s) => s.selectedRouteId);
  const query = usePlan(submitted);
  const plan = query.data;
  return (
    <div className="flex h-full flex-col">
      <HeatmapController plan={plan} />
      <div className="flex min-h-0 flex-1">
        <aside className="flex w-[400px] shrink-0 flex-col overflow-y-auto border-r border-slate-200 bg-slate-50">
          <header className="border-b border-slate-200 bg-white px-4 py-3">
            <h1 className="text-base font-bold tracking-tight">Weather-Aware Truck Routing</h1>
            <p className="text-xs text-slate-500">
              Compare routes by forecast weather at each checkpoint’s ETA.
            </p>
          </header>
          <div className="space-y-4 p-4">
            <PlanForm onSubmit={submit} loading={query.isFetching} />
            <ResultsPanel query={query} submitted={submitted !== null} selectedId={selectedId} />
          </div>
        </aside>
        <main className="relative min-w-0 flex-1" aria-label="Map">
          <Suspense fallback={<MapFallback />}>
            <MapView plan={plan} selectedId={selectedId} />
          </Suspense>
          {plan && (
            <div className="pointer-events-none absolute inset-x-3 bottom-3 z-10 mx-auto max-w-3xl">
              <ForecastSlider
                departure={plan.assumptions.departure_time}
                route={plan.routes.find(
                  (r) => r.id === (selectedId ?? plan.recommendation.route_id),
                )}
              />
            </div>
          )}
        </main>
      </div>
      <AssumptionsFooter plan={plan} />
    </div>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Shell />
    </QueryClientProvider>
  );
}
