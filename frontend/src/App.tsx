import { QueryClientProvider } from '@tanstack/react-query';
import { lazy, Suspense, useState } from 'react';
import type { PlanInputs } from './api/hooks';
import { usePlan } from './api/hooks';
import type { Plan, RouteId } from './api/types';
import { AssumptionsFooter } from './app/AssumptionsFooter';
import { BottomSheet } from './app/BottomSheet';
import { snapHeight, type Snap } from './app/sheet';
import { queryClient } from './app/queryClient';
import { ResultsPanel } from './app/ResultsPanel';
import { ForecastSlider, HeatmapController } from './features/heatmap';
import { PlanForm } from './features/plan-form';
import { DESKTOP_QUERY, useMediaQuery } from './lib/useMediaQuery';
import { useUi } from './store/ui';

// MapLibre + deck.gl live in their own chunk so the form is interactive first (docs/04 §7).
const MapView = lazy(() => import('./features/map/MapView').then((m) => ({ default: m.MapView })));

function MapFallback() {
  return <div className="h-full w-full bg-[#e9eef2]" aria-label="Loading map" />;
}

const SCENARIO_LABEL = { winter_storm: 'winter storm', high_wind: 'high wind' } as const;

function Slider({ plan, selectedId }: { plan: Plan; selectedId: RouteId | null }) {
  return (
    <ForecastSlider
      departure={plan.assumptions.departure_time}
      route={plan.routes.find((r) => r.id === (selectedId ?? plan.recommendation.route_id))}
    />
  );
}

function Title() {
  return (
    <>
      <h1 className="text-base font-bold tracking-tight">Weather-Aware Truck Routing</h1>
      <p className="text-xs text-slate-500 max-lg:hidden">
        Compare routes by forecast weather at each checkpoint’s ETA.
      </p>
    </>
  );
}

function Shell() {
  const submitted = useUi((s) => s.submitted);
  const submit = useUi((s) => s.submit);
  const selectedId = useUi((s) => s.selectedRouteId);
  const query = usePlan(submitted);
  const plan = query.data;
  const desktop = useMediaQuery(DESKTOP_QUERY);
  const [formOpen, setFormOpen] = useState(true);
  const [snap, setSnap] = useState<Snap>('half');

  const onSubmit = (inputs: PlanInputs) => {
    submit(inputs);
    if (!desktop) {
      setFormOpen(false); // give the map the screen on phones
      setSnap('peek');
    }
  };

  const form = <PlanForm onSubmit={onSubmit} loading={query.isFetching} />;
  const results = (
    <ResultsPanel query={query} submitted={submitted !== null} selectedId={selectedId} />
  );
  const map = (
    <Suspense fallback={<MapFallback />}>
      <MapView plan={plan} selectedId={selectedId} />
    </Suspense>
  );

  if (desktop) {
    return (
      <div className="flex h-full flex-col">
        <HeatmapController plan={plan} />
        <a
          href="#results"
          className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-white focus:p-2"
        >
          Skip to results
        </a>
        <div className="flex min-h-0 flex-1">
          <aside className="flex w-[400px] shrink-0 flex-col overflow-y-auto border-r border-slate-200 bg-slate-50">
            <header className="border-b border-slate-200 bg-white px-4 py-3">
              <Title />
            </header>
            <div className="space-y-4 p-4">
              {form}
              <div id="results" tabIndex={-1}>
                {results}
              </div>
            </div>
          </aside>
          <main className="relative min-w-0 flex-1" aria-label="Map">
            {map}
            {plan && (
              <div className="pointer-events-none absolute inset-x-3 bottom-3 z-10 mx-auto max-w-3xl">
                <Slider plan={plan} selectedId={selectedId} />
              </div>
            )}
          </main>
        </div>
        <AssumptionsFooter plan={plan} />
      </div>
    );
  }

  const sheetPx = snapHeight(snap, window.innerHeight);
  return (
    <div className="relative h-full overflow-hidden">
      <HeatmapController plan={plan} />
      <main className="absolute inset-0" aria-label="Map">
        {map}
      </main>
      <header className="absolute inset-x-2 top-2 z-30 max-h-[85%] overflow-y-auto rounded-xl bg-white/95 shadow-lg ring-1 ring-slate-200 backdrop-blur">
        <div className="flex items-center gap-2 px-3 py-2">
          <div className="min-w-0 flex-1">
            <Title />
            {plan?.assumptions.scenario && (
              <span className="text-[11px] font-semibold text-amber-800">
                ⚠ Simulated weather · {SCENARIO_LABEL[plan.assumptions.scenario]}
              </span>
            )}
          </div>
          <button
            type="button"
            className="shrink-0 rounded-md bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white"
            aria-expanded={formOpen}
            aria-controls="trip-form"
            onClick={() => setFormOpen((o) => !o)}
          >
            {formOpen ? 'Hide trip' : 'Edit trip'}
          </button>
        </div>
        <div id="trip-form" hidden={!formOpen} className="border-t border-slate-200 p-3">
          {form}
        </div>
      </header>
      {plan && (
        <div
          className="pointer-events-none absolute inset-x-2 z-10 motion-safe:transition-[bottom] motion-safe:duration-200"
          style={{ bottom: sheetPx + 8 }}
        >
          <Slider plan={plan} selectedId={selectedId} />
        </div>
      )}
      {submitted && (
        <BottomSheet snap={snap} onSnap={setSnap} label="Results">
          <div className="space-y-3">
            {results}
            <AssumptionsFooter plan={plan} />
          </div>
        </BottomSheet>
      )}
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
