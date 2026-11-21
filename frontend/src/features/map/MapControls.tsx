import { useState } from 'react';
import { LEVELS, LEVEL_ORDER, scoreColor } from '../../lib/risk';
import { ROUTE_COLORS } from '../../lib/routes';
import { useUi } from '../../store/ui';

const gradient = `linear-gradient(to right, ${Array.from({ length: 41 }, (_, i) => {
  const [r, g, b, a] = scoreColor(i / 10);
  return `rgba(${r},${g},${b},${(a / 255).toFixed(2)}) ${(i / 40) * 100}%`;
}).join(', ')})`;

/** Legend and layer toggles, collapsible, bottom-right above the slider. */
export function MapControls() {
  const [open, setOpen] = useState(
    () => window.matchMedia?.('(min-width: 1024px)').matches ?? true,
  );
  const heatmapVisible = useUi((s) => s.heatmapVisible);
  const heatmapOpacity = useUi((s) => s.heatmapOpacity);
  const showAllRoutes = useUi((s) => s.showAllRoutes);
  const showCheckpoints = useUi((s) => s.showCheckpoints);
  const setLayer = useUi((s) => s.setLayer);
  return (
    <div className="absolute right-4 top-4 z-10 w-64 rounded-2xl border border-black/10 bg-white/80 text-xs text-neutral-800 shadow-2xl shadow-black/15 backdrop-blur-2xl dark:border-white/10 dark:bg-black/75 dark:text-neutral-200 dark:shadow-black/80 max-lg:top-[124px] max-lg:w-auto max-lg:max-w-[15rem]">
      <button
        type="button"
        className="flex w-full items-center justify-between px-3.5 py-2.5 font-semibold text-neutral-900 transition-colors hover:text-black dark:text-neutral-100 dark:hover:text-white"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        Legend & layers <span aria-hidden="true">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <div className="space-y-3 px-3.5 pb-3.5">
          <ul
            className="grid grid-cols-2 gap-1 text-neutral-700 dark:text-neutral-300"
            aria-label="Risk levels"
          >
            {[...LEVEL_ORDER, 'UNKNOWN' as const].map((lvl) => (
              <li key={lvl} className="flex items-center gap-1.5">
                <span
                  className={`h-2.5 w-2.5 rounded-sm ${LEVELS[lvl].swatch}`}
                  aria-hidden="true"
                />
                <span aria-hidden="true">{LEVELS[lvl].icon}</span>
                {LEVELS[lvl].label}
              </li>
            ))}
          </ul>
          <div>
            <div className="mb-1 text-neutral-500 dark:text-neutral-400">
              Heatmap risk score 0 to 4
            </div>
            <div
              className="h-2 rounded-full ring-1 ring-black/10 dark:ring-white/15"
              style={{ background: gradient }}
            />
          </div>
          <ul
            className="flex justify-between text-neutral-700 dark:text-neutral-300"
            aria-label="Route colours"
          >
            {(Object.keys(ROUTE_COLORS) as (keyof typeof ROUTE_COLORS)[]).map((id) => (
              <li key={id} className="flex items-center gap-1 whitespace-nowrap">
                <span
                  className="h-1 w-4 rounded"
                  style={{ background: ROUTE_COLORS[id].hex }}
                  aria-hidden="true"
                />
                Route {id}
              </li>
            ))}
          </ul>
          <fieldset className="space-y-1.5 border-t border-black/10 pt-2 dark:border-white/10">
            <legend className="sr-only">Layers</legend>
            <Toggle
              label="Weather heatmap"
              checked={heatmapVisible}
              onChange={(v) => setLayer({ heatmapVisible: v })}
            />
            <label className="flex items-center gap-2 pl-5 text-neutral-600 dark:text-neutral-400">
              Opacity
              <input
                type="range"
                min={0.2}
                max={1}
                step={0.05}
                value={heatmapOpacity}
                disabled={!heatmapVisible}
                onChange={(e) => setLayer({ heatmapOpacity: Number(e.target.value) })}
                className="w-full accent-black dark:accent-white"
                aria-label="Heatmap opacity"
              />
            </label>
            <Toggle
              label="Show all routes"
              checked={showAllRoutes}
              onChange={(v) => setLayer({ showAllRoutes: v })}
            />
            <Toggle
              label="Show checkpoints"
              checked={showCheckpoints}
              onChange={(v) => setLayer({ showCheckpoints: v })}
            />
          </fieldset>
        </div>
      )}
    </div>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex min-h-6 cursor-pointer items-center gap-2 py-0.5 text-neutral-700 transition-colors hover:text-black dark:text-neutral-300 dark:hover:text-white">
      <input
        type="checkbox"
        className="h-4 w-4 rounded border-black/20 bg-black/5 text-black accent-black focus:ring-0 dark:border-white/20 dark:bg-white/10 dark:text-white dark:accent-white"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
      {label}
    </label>
  );
}
