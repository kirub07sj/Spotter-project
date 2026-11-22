import { LEVELS, LEVEL_ORDER, scoreColor } from '../../lib/risk';
import { ROUTE_COLORS } from '../../lib/routes';
import { useUi } from '../../store/ui';

const gradient = `linear-gradient(to right, ${Array.from({ length: 41 }, (_, i) => {
  const [r, g, b, a] = scoreColor(i / 10);
  return `rgba(${r},${g},${b},${(a / 255).toFixed(2)}) ${(i / 40) * 100}%`;
}).join(', ')})`;

/** Legend and layer toggles, collapsible, bottom-right above the slider. */
export function MapControls() {
  const legendOpen = useUi((s) => s.legendOpen);
  const toggleLegend = useUi((s) => s.toggleLegend);
  const checkpointTableOpen = useUi((s) => s.checkpointTableOpen);
  const toggleCheckpointTable = useUi((s) => s.toggleCheckpointTable);
  const heatmapVisible = useUi((s) => s.heatmapVisible);
  const heatmapOpacity = useUi((s) => s.heatmapOpacity);
  const showAllRoutes = useUi((s) => s.showAllRoutes);
  const showCheckpoints = useUi((s) => s.showCheckpoints);
  const setLayer = useUi((s) => s.setLayer);

  return (
    <>
      {/* Top right toggles: positioned to the left of the zoom buttons (right-16) */}
      <div className="absolute right-16 top-3.5 z-20 flex items-center gap-2 max-lg:top-[124px] max-lg:right-4">
        <button
          type="button"
          onClick={toggleLegend}
          aria-expanded={legendOpen}
          aria-label="Toggle map legend and layers"
          className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold backdrop-blur-2xl transition-all shadow-md ${
            legendOpen
              ? 'border-neutral-900 bg-neutral-900 text-white shadow-black/20 dark:border-white dark:bg-white dark:text-neutral-950'
              : 'border-black/10 bg-white/70 text-neutral-700 hover:bg-white/90 hover:text-black dark:border-white/15 dark:bg-black/65 dark:text-neutral-300 dark:hover:bg-black/85 dark:hover:text-white'
          }`}
        >
          <span aria-hidden="true" className="text-xs">
            🗺
          </span>
          <span>Legend</span>
        </button>

        <button
          type="button"
          onClick={toggleCheckpointTable}
          aria-expanded={checkpointTableOpen}
          aria-label="Toggle checkpoint details"
          className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold backdrop-blur-2xl transition-all shadow-md ${
            checkpointTableOpen
              ? 'border-neutral-900 bg-neutral-900 text-white shadow-black/20 dark:border-white dark:bg-white dark:text-neutral-950'
              : 'border-black/10 bg-white/70 text-neutral-700 hover:bg-white/90 hover:text-black dark:border-white/15 dark:bg-black/65 dark:text-neutral-300 dark:hover:bg-black/85 dark:hover:text-white'
          }`}
        >
          <span aria-hidden="true" className="text-xs">
            📍
          </span>
          <span>Checkpoints</span>
        </button>
      </div>

      {/* Legend & layers card: positioned to the left of the zoom buttons (right-16) */}
      {legendOpen && (
        <div className="glass-panel absolute right-16 top-14 z-20 w-64 text-xs overflow-hidden max-lg:top-[168px] max-lg:right-4 max-lg:w-auto max-lg:max-w-[15rem]">
          <div className="glass-header flex items-center justify-between px-3.5 py-2.5 font-semibold text-neutral-900 dark:text-white">
            <span>Legend & layers</span>
            <button
              type="button"
              onClick={toggleLegend}
              className="text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 text-xs px-1"
              aria-label="Close legend"
            >
              ✕
            </button>
          </div>
          <div className="space-y-3 px-3.5 py-3">
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
        </div>
      )}
    </>
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
