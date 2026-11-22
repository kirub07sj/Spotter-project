import { useState } from 'react';
import type { Plan } from '../../api/types';
import { ROUTE_BADGE } from '../../lib/routes';

const SCENARIO_LABEL = { winter_storm: 'winter storm', high_wind: 'high wind' } as const;

/** Answer first: which route, and why, in one line (docs/04 §1). */
export function RecommendationBanner({ plan }: { plan: Plan }) {
  const [open, setOpen] = useState(false);
  const { recommendation: rec } = plan;
  const route = plan.routes.find((r) => r.id === rec.route_id);
  const unsafe = rec.status === 'NO_SAFE_ROUTE';
  const gaps = plan.warnings.some((w) => w.code === 'WEATHER_GAPS');
  const scenario = plan.assumptions.scenario;
  const [first, ...rest] = rec.reasons;
  return (
    <section
      aria-labelledby="rec-title"
      className={`rounded-2xl border p-3.5 backdrop-blur-md shadow-md ${
        unsafe
          ? 'border-rose-200 bg-rose-50/95 text-rose-950 dark:border-rose-500/30 dark:bg-rose-950/40 dark:text-rose-100'
          : 'border-emerald-200 bg-emerald-50/95 text-emerald-950 dark:border-emerald-500/30 dark:bg-emerald-950/40 dark:text-emerald-100'
      }`}
    >
      {scenario && (
        <p className="mb-2 inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-900 ring-1 ring-amber-500/30 dark:bg-amber-500/20 dark:text-amber-300 dark:ring-amber-400/30">
          <span aria-hidden="true">⚠</span> Simulated weather · {SCENARIO_LABEL[scenario]}
        </p>
      )}
      {unsafe && (
        <p role="alert" className="mb-1 text-sm font-bold text-rose-800 dark:text-rose-300">
          No route is safe to start at this time
        </p>
      )}
      <div className="flex items-start gap-2">
        <span
          className={`mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-sm font-bold text-white shadow-md ${ROUTE_BADGE[rec.route_id]}`}
          aria-hidden="true"
        >
          {rec.route_id}
        </span>
        <div className="min-w-0 flex-1">
          <h2 id="rec-title" className="text-sm font-semibold text-neutral-900 dark:text-white">
            {unsafe ? 'Least risky: ' : 'Recommended: '}Route {rec.route_id}
            <span className="font-normal text-neutral-600 dark:text-neutral-300">
              {' '}
              · {route?.label}
            </span>
          </h2>
          <p className="text-sm text-neutral-800 dark:text-neutral-200">
            {first ?? 'Only one route is available for this trip.'}
          </p>
          {rest.length > 0 && (
            <>
              <button
                type="button"
                className="mt-1 text-xs font-medium text-neutral-900 underline underline-offset-2 hover:text-black dark:text-white dark:hover:text-neutral-200"
                aria-expanded={open}
                onClick={() => setOpen((o) => !o)}
              >
                {open ? 'Hide reasons' : 'Why?'}
              </button>
              {open && (
                <ul className="mt-1 list-disc space-y-0.5 pl-4 text-xs text-neutral-700 dark:text-neutral-300">
                  {rec.reasons.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
        <span
          className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold shadow-sm ${unsafe ? 'bg-rose-600 text-white' : 'bg-emerald-600 text-white'}`}
        >
          {unsafe ? 'No safe route' : 'OK'}
        </span>
      </div>
      {gaps && (
        <p className="mt-2 inline-flex items-center gap-1 rounded-full border border-neutral-200 bg-white/80 px-2.5 py-0.5 text-xs text-neutral-700 dark:border-white/10 dark:bg-white/10 dark:text-neutral-300">
          <span aria-hidden="true">?</span> Some checkpoints have no forecast data
        </p>
      )}
    </section>
  );
}
