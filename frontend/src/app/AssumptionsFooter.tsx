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
    <footer className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-slate-200 bg-white px-3 py-1.5 text-[11px] text-slate-600">
      <span>Risk from {metric} (D-04)</span>
      <span>· Truck {cap}</span>
      <span>· Hours-of-service breaks not modelled</span>
      <span>· {sources}</span>
      <span>· Times in your time zone</span>
      {a?.scenario && (
        <span className="rounded-full bg-amber-100 px-2 py-0.5 font-semibold text-amber-900 ring-1 ring-amber-300">
          Simulated weather · {SCENARIO_LABEL[a.scenario]}
        </span>
      )}
    </footer>
  );
}
