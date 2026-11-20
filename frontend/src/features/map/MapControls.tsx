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
  const [open, setOpen] = useState(true);
  const heatmapVisible = useUi((s) => s.heatmapVisible);
  const heatmapOpacity = useUi((s) => s.heatmapOpacity);
  const showAllRoutes = useUi((s) => s.showAllRoutes);
  const showCheckpoints = useUi((s) => s.showCheckpoints);
  const setLayer = useUi((s) => s.setLayer);
  return (
    <div className="absolute right-2 top-24 z-10 w-56 rounded-lg bg-white/95 text-xs shadow-lg ring-1 ring-slate-200 backdrop-blur max-lg:hidden">
      <button
        type="button"
        className="flex w-full items-center justify-between px-3 py-2 font-semibold"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        Legend & layers <span aria-hidden="true">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <div className="space-y-3 px-3 pb-3">
          <ul className="grid grid-cols-2 gap-1" aria-label="Risk levels">
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
            <div className="mb-1 text-slate-500">Heatmap risk score 0 to 4</div>
            <div
              className="h-2 rounded-full ring-1 ring-slate-200"
              style={{ background: gradient }}
            />
          </div>
          <ul className="flex justify-between" aria-label="Route colours">
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
          <fieldset className="space-y-1.5 border-t border-slate-200 pt-2">
            <legend className="sr-only">Layers</legend>
            <Toggle
              label="Weather heatmap"
              checked={heatmapVisible}
              onChange={(v) => setLayer({ heatmapVisible: v })}
            />
            <label className="flex items-center gap-2 pl-5 text-slate-600">
              Opacity
              <input
                type="range"
                min={0.2}
                max={1}
                step={0.05}
                value={heatmapOpacity}
                disabled={!heatmapVisible}
                onChange={(e) => setLayer({ heatmapOpacity: Number(e.target.value) })}
                className="w-full"
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
    <label className="flex cursor-pointer items-center gap-2">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      {label}
    </label>
  );
}
