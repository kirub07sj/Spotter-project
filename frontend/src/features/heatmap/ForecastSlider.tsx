import { useMemo } from 'react';
import type { Route } from '../../api/types';
import { formatOffset, spokenOffset } from '../../lib/format';
import { MAX_HOUR, useUi } from '../../store/ui';
import { useHeatmapStore } from './store';
import { usePlayback } from './usePlayback';

interface Props {
  departure: string;
  route: Route | undefined;
}

const HOUR_TICKS = [0, 6, 12, 18, 24, 30, 36, 42, 48];

/** 0-48 h forecast timeline (D-14). Only this component and the map subscribe to `hour`. */
export function ForecastSlider({ departure, route }: Props) {
  const hour = useUi((s) => s.hour);
  const playing = useUi((s) => s.playing);
  const setHour = useUi((s) => s.setHour);
  const setPlaying = useUi((s) => s.setPlaying);
  const status = useHeatmapStore((s) => s.status);
  const ready = useHeatmapStore((s) => s.ready);
  const total = useHeatmapStore((s) => s.bitmaps.length);
  usePlayback();

  const etaTicks = useMemo(() => {
    if (!route) return [];
    const t0 = new Date(departure).getTime();
    return route.checkpoints
      .map((cp) => (new Date(cp.eta).getTime() - t0) / 3_600_000)
      .filter((h) => h >= 0 && h <= MAX_HOUR);
  }, [route, departure]);

  const loading = status === 'loading' || (status === 'rendering' && ready === 0);
  const disabled = loading;

  const togglePlay = () => {
    if (!playing && hour >= MAX_HOUR) setHour(0);
    setPlaying(!playing);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    const step = e.shiftKey ? 6 : 1;
    if (e.key === 'ArrowRight' || e.key === 'ArrowUp') setHour(Math.floor(hour) + step);
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') setHour(Math.ceil(hour) - step);
    else if (e.key === ' ') togglePlay();
    else if (e.key === 'Home') setHour(0);
    else if (e.key === 'End') setHour(MAX_HOUR);
    else return;
    e.preventDefault();
  };

  return (
    <div className="pointer-events-auto rounded-xl bg-white/95 px-3 pb-2 pt-2 shadow-lg ring-1 ring-slate-200 backdrop-blur">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={togglePlay}
          disabled={disabled}
          aria-label={playing ? 'Pause forecast playback' : 'Play forecast'}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-900 text-white disabled:bg-slate-300"
        >
          <span aria-hidden="true">{playing ? '❚❚' : '▶'}</span>
        </button>
        <div className="relative min-w-0 flex-1">
          <input
            type="range"
            min={0}
            max={MAX_HOUR}
            step={0.05}
            value={hour}
            disabled={disabled}
            onChange={(e) => {
              if (playing) setPlaying(false);
              setHour(Number(e.target.value));
            }}
            onKeyDown={onKeyDown}
            aria-label="Forecast time"
            aria-valuetext={spokenOffset(hour, departure)}
            className="forecast-range w-full"
          />
          <div className="pointer-events-none relative mt-0.5 h-3" aria-hidden="true">
            {etaTicks.map((h, i) => (
              <span
                key={i}
                className="absolute top-0 h-1.5 w-px bg-slate-900"
                style={{ left: `${(h / MAX_HOUR) * 100}%` }}
              />
            ))}
            {HOUR_TICKS.map((h) => (
              <span
                key={h}
                className="absolute top-1.5 -translate-x-1/2 text-[10px] leading-none text-slate-400"
                style={{ left: `${(h / MAX_HOUR) * 100}%` }}
              >
                {h}
              </span>
            ))}
          </div>
        </div>
        <div className="w-40 shrink-0 text-right">
          <div className="text-sm font-semibold text-slate-900">
            {formatOffset(hour, departure)}
          </div>
          <div className="text-[11px] text-slate-500" aria-live="polite">
            {loading
              ? 'Loading forecast…'
              : status === 'error'
                ? 'Heatmap unavailable'
                : status === 'rendering'
                  ? `rendering ${ready}/${total || 49}`
                  : 'ticks = checkpoint ETAs'}
          </div>
        </div>
      </div>
    </div>
  );
}
