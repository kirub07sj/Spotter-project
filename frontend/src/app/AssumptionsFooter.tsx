import type { Plan } from '../api/types';

const SCENARIO_LABEL = { winter_storm: 'winter storm', high_wind: 'high wind' } as const;

/** Always-visible assumptions (docs/04 §1 rule 5, D-04, D-07, D-20). */
export function AssumptionsFooter({ plan }: { plan: Plan | undefined }) {
  const a = plan?.assumptions;
  const metric = a?.wind_metric === 'sustained' ? 'sustained wind' : 'wind gusts';
  const cap = a
    ? a.truck_max_speed_mph > 0
      ? `speed capped at ${a.truck_max_speed_mph} mph`
      : 'no speed cap'
    : 'speed capped at 65 mph';
  const sources =
    a?.providers === 'fake'
      ? 'Demo data (offline providers)'
      : 'Routing: Mapbox · Weather: Open-Meteo';
  return (
    <footer className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-black/10 bg-black/[0.03] px-4 py-2 text-[11px] text-neutral-600 dark:border-white/10 dark:bg-black/40 dark:text-neutral-400">
      <span>Risk from {metric} (D-04)</span>
      <span>· Truck {cap}</span>
      <span>· Hours-of-service breaks not modelled</span>
      <span>· {sources}</span>
      <span>· Times in your time zone</span>
      {a?.scenario && (
        <span className="rounded-full bg-amber-500/20 px-2 py-0.5 font-semibold text-amber-800 ring-1 ring-amber-400/40 dark:text-amber-300 dark:ring-amber-400/30">
          Simulated weather · {SCENARIO_LABEL[a.scenario]}
        </span>
      )}
    </footer>
  );
}
