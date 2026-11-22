import { QueryClientProvider } from '@tanstack/react-query';
import { lazy, Suspense, useEffect, useState } from 'react';
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
import { CheckpointPanel } from './features/routes';
import { DESKTOP_QUERY, useMediaQuery } from './lib/useMediaQuery';
import { useUi } from './store/ui';

// MapLibre + deck.gl live in their own chunk so the form is interactive first (docs/04 §7).
const MapView = lazy(() => import('./features/map/MapView').then((m) => ({ default: m.MapView })));

function MapFallback() {
  return (
    <div className="h-full w-full bg-neutral-100 dark:bg-neutral-950" aria-label="Loading map" />
  );
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

function ThemeToggle() {
  const theme = useUi((s) => s.theme);
  const toggleTheme = useUi((s) => s.toggleTheme);

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      className="flex shrink-0 items-center gap-1.5 rounded-full border border-black/10 bg-black/5 px-2.5 py-1 text-xs font-medium text-neutral-800 transition-colors hover:bg-black/10 dark:border-white/15 dark:bg-white/10 dark:text-neutral-200 dark:hover:bg-white/15"
    >
      <span aria-hidden="true" className="text-xs">
        {theme === 'dark' ? '☀' : '🌙'}
      </span>
      <span className="text-[11px] font-semibold tracking-wide">
        {theme === 'dark' ? 'Light' : 'Dark'}
      </span>
    </button>
  );
}

function Title() {
  return (
    <div>
      <div className="flex items-center gap-2">
        <span
          className="flex h-2.5 w-2.5 rounded-full bg-neutral-900 shadow-[0_0_8px_rgba(0,0,0,0.4)] dark:bg-white dark:shadow-[0_0_8px_rgba(255,255,255,0.8)]"
          aria-hidden="true"
        />
        <h1 className="text-base font-bold tracking-tight text-neutral-900 dark:text-white">
          Weather-Aware Truck Routing
        </h1>
      </div>
      <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400 max-lg:hidden">
        Compare routes by forecast weather at each checkpoint’s ETA.
      </p>
    </div>
  );
}

function Shell() {
  const submitted = useUi((s) => s.submitted);
  const submit = useUi((s) => s.submit);
  const selectedId = useUi((s) => s.selectedRouteId);
  const theme = useUi((s) => s.theme);
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

  useEffect(() => {
    if (plan && desktop) {
      document.getElementById('results')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [plan, desktop]);

  const form = <PlanForm onSubmit={onSubmit} loading={query.isFetching} />;
  const desktopResults = (
    <ResultsPanel
      query={query}
      submitted={submitted !== null}
      selectedId={selectedId}
      showCheckpoints={false}
    />
  );
  const mobileResults = (
    <ResultsPanel
      query={query}
      submitted={submitted !== null}
      selectedId={selectedId}
      showCheckpoints={true}
    />
  );
  const map = (
    <Suspense fallback={<MapFallback />}>
      <MapView plan={plan} selectedId={selectedId} />
    </Suspense>
  );

  const rootClass =
    theme === 'dark'
      ? 'dark relative h-full w-full overflow-hidden bg-black font-sans'
      : 'relative h-full w-full overflow-hidden bg-neutral-100 font-sans';

  if (desktop) {
    return (
      <div className={rootClass}>
        <HeatmapController plan={plan} />
        <a
          href="#results"
          className="sr-only focus:not-sr-only focus:absolute focus:left-6 focus:top-6 focus:z-50 focus:rounded-md focus:bg-black focus:px-3 focus:py-2 focus:text-white focus:shadow-lg dark:focus:bg-white dark:focus:text-black"
        >
          Skip to results
        </a>
        <main className="absolute inset-0 z-0 h-full w-full" aria-label="Map">
          {map}
        </main>
        <aside
          className="pointer-events-auto absolute bottom-4 left-4 top-4 z-20 flex w-[420px] max-w-[calc(100vw-2rem)] flex-col rounded-3xl overflow-hidden border border-black/10 bg-white/95 text-neutral-900 shadow-2xl shadow-black/10 backdrop-blur-2xl dark:border-white/10 dark:bg-black/85 dark:text-white dark:shadow-black/80"
          aria-label="Trip planning and route comparison"
        >
          <header className="border-b border-black/[0.06] bg-neutral-50/80 px-5 py-4 backdrop-blur-md dark:border-white/10 dark:bg-white/[0.03]">
            <div className="flex items-start justify-between gap-3">
              <Title />
              <ThemeToggle />
            </div>
            {plan?.assumptions.scenario && (
              <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-0.5 text-[11px] font-semibold text-amber-800 ring-1 ring-amber-500/20 dark:bg-amber-500/20 dark:text-amber-300 dark:ring-amber-400/30">
                <span aria-hidden="true">⚠</span> Simulated weather ·{' '}
                {SCENARIO_LABEL[plan.assumptions.scenario]}
              </div>
            )}
          </header>
          <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
            {form}
            <div id="results" tabIndex={-1} className="outline-none">
              {desktopResults}
            </div>
          </div>
          <AssumptionsFooter plan={plan} />
        </aside>
        {plan && <CheckpointPanel plan={plan} selectedId={selectedId} />}
        {plan && (
          <div className="pointer-events-none absolute bottom-5 left-4 right-4 z-10 mx-auto max-w-xl lg:left-[440px] lg:right-6 lg:max-w-2xl">
            <Slider plan={plan} selectedId={selectedId} />
          </div>
        )}
      </div>
    );
  }

  const sheetPx = snapHeight(snap, window.innerHeight);
  return (
    <div className={rootClass}>
      <HeatmapController plan={plan} />
      <main className="absolute inset-0" aria-label="Map">
        {map}
      </main>
      <header className="absolute inset-x-2 top-2 z-30 max-h-[85%] overflow-y-auto rounded-3xl border border-black/10 bg-white/95 p-3 text-neutral-900 shadow-2xl shadow-black/15 backdrop-blur-2xl dark:border-white/10 dark:bg-black/90 dark:text-white dark:shadow-black/80">
        <div className="flex items-center gap-2">
          <div className="min-w-0 flex-1">
            <Title />
            {plan?.assumptions.scenario && (
              <span className="text-[11px] font-semibold text-amber-700 dark:text-amber-400">
                ⚠ Simulated weather · {SCENARIO_LABEL[plan.assumptions.scenario]}
              </span>
            )}
          </div>
          <ThemeToggle />
          <button
            type="button"
            className="shrink-0 rounded-lg bg-black px-3 py-1.5 text-xs font-semibold text-white shadow-md hover:bg-neutral-800 dark:bg-white dark:text-black dark:hover:bg-neutral-200"
            aria-expanded={formOpen}
            aria-controls="trip-form"
            onClick={() => setFormOpen((o) => !o)}
          >
            {formOpen ? 'Hide trip' : 'Edit trip'}
          </button>
        </div>
        <div
          id="trip-form"
          hidden={!formOpen}
          className="mt-3 border-t border-black/10 pt-3 dark:border-white/10"
        >
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
            {mobileResults}
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
