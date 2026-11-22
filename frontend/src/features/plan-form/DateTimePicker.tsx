import { useEffect, useRef, useState } from 'react';
import { maxFutureLocal, nowLocal } from './schema';

interface Props {
  value: string;
  onChange: (val: string) => void;
  error?: string;
  disabled?: boolean;
}

const DAYS_SHORT = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

function parseDate(isoLocal: string): Date | null {
  if (!isoLocal) return null;
  const d = new Date(isoLocal);
  return Number.isNaN(d.getTime()) ? null : d;
}

function pad(n: number): string {
  return String(n).padStart(2, '0');
}

export function DateTimePicker({ value, onChange, error, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const [monthOffset, setMonthOffset] = useState(0);

  // Reference timestamp on component mount to satisfy purity rules
  const [now] = useState(() => new Date());
  const minStr = nowLocal(now);
  const maxStr = maxFutureLocal(now);

  const minDate = new Date(now);
  minDate.setHours(0, 0, 0, 0);

  const maxDate = new Date(now.getTime() + 7 * 24 * 3600 * 1000);
  maxDate.setHours(23, 59, 59, 999);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  // Reset month view when opening
  const handleToggle = () => {
    if (!disabled) {
      setMonthOffset(0);
      setOpen((o) => !o);
    }
  };

  const parsed = parseDate(value) ?? now;

  // View year and month calculated from parsed date + month offset
  const viewDate = new Date(parsed.getFullYear(), parsed.getMonth() + monthOffset, 1);
  const viewYear = viewDate.getFullYear();
  const viewMonth = viewDate.getMonth();

  const firstDayOfMonth = new Date(viewYear, viewMonth, 1).getDay();
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();

  const selYear = parsed.getFullYear();
  const selMonth = parsed.getMonth();
  const selDay = parsed.getDate();
  const selHours = parsed.getHours();
  const selMinutes = parsed.getMinutes();

  const handleSelectDay = (day: number) => {
    const updated = new Date(parsed);
    updated.setFullYear(viewYear, viewMonth, day);

    // If day is today and time is in past, snap forward to current time
    if (updated.getTime() < now.getTime()) {
      updated.setHours(now.getHours(), now.getMinutes());
    }

    const isoString = `${updated.getFullYear()}-${pad(updated.getMonth() + 1)}-${pad(updated.getDate())}T${pad(updated.getHours())}:${pad(updated.getMinutes())}`;
    onChange(isoString);
  };

  const handleTimeChange = (hours: number, minutes: number) => {
    const updated = new Date(parsed);
    updated.setHours(hours, minutes, 0, 0);

    // Enforce future limiter: if less than now, snap to now
    const clamped = updated.getTime() < now.getTime() ? now : updated;
    const isoString = `${clamped.getFullYear()}-${pad(clamped.getMonth() + 1)}-${pad(clamped.getDate())}T${pad(clamped.getHours())}:${pad(clamped.getMinutes())}`;
    onChange(isoString);
  };

  const setPreset = (offsetHours: number) => {
    const target = new Date(now.getTime() + offsetHours * 3600 * 1000);
    const isoString = `${target.getFullYear()}-${pad(target.getMonth() + 1)}-${pad(target.getDate())}T${pad(target.getHours())}:${pad(target.getMinutes())}`;
    onChange(isoString);
    setOpen(false);
  };

  const monthName = viewDate.toLocaleDateString(undefined, {
    month: 'long',
    year: 'numeric',
  });

  return (
    <div ref={containerRef} className="relative w-full">
      {/* Shadcn-styled DateTime Input with Calendar icon trigger */}
      <div className="relative flex items-center">
        <input
          id="departure"
          type="datetime-local"
          min={minStr}
          max={maxStr}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? 'trip-error' : undefined}
          className={`w-full rounded-xl border px-3 py-2 pr-9 text-xs font-medium text-neutral-900 transition-all shadow-sm backdrop-blur-2xl [color-scheme:light] focus:outline-none dark:text-white dark:[color-scheme:dark] ${
            error
              ? 'border-rose-400 bg-rose-50/50 focus:border-rose-500 focus:ring-1 focus:ring-rose-500 dark:border-rose-500/40 dark:bg-rose-950/20'
              : 'border-black/10 bg-white/50 hover:bg-white/70 focus:border-black focus:ring-1 focus:ring-black dark:border-white/15 dark:bg-white/[0.05] dark:hover:bg-white/[0.08] dark:focus:border-white/40 dark:focus:bg-white/[0.1] dark:focus:ring-white/20'
          }`}
        />
        <button
          type="button"
          onClick={handleToggle}
          disabled={disabled}
          aria-expanded={open}
          aria-haspopup="dialog"
          aria-label="Open date and time picker"
          className="absolute right-2 flex h-6 w-6 items-center justify-center rounded-lg text-neutral-500 hover:bg-black/5 hover:text-black dark:text-neutral-400 dark:hover:bg-white/10 dark:hover:text-white transition-colors"
        >
          <svg
            className="h-3.5 w-3.5 shrink-0"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <rect width="18" height="18" x="3" y="4" rx="2" ry="2" />
            <line x1="16" x2="16" y1="2" y2="6" />
            <line x1="8" x2="8" y1="2" y2="6" />
            <line x1="3" x2="21" y1="10" y2="10" />
          </svg>
        </button>
      </div>

      {/* Shadcn Popover Card */}
      {open && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Choose departure date and time"
          className="glass-panel absolute left-0 top-full z-50 mt-2 w-72 p-3 text-xs shadow-2xl animate-in fade-in zoom-in-95 duration-150"
        >
          {/* Calendar Header */}
          <div className="flex items-center justify-between pb-2 border-b border-black/5 dark:border-white/10">
            <span className="font-semibold text-neutral-900 dark:text-white capitalize">
              {monthName}
            </span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setMonthOffset((o) => o - 1)}
                aria-label="Previous month"
                className="flex h-6 w-6 items-center justify-center rounded-md hover:bg-black/10 dark:hover:bg-white/10 text-neutral-600 dark:text-neutral-300"
              >
                ‹
              </button>
              <button
                type="button"
                onClick={() => setMonthOffset((o) => o + 1)}
                aria-label="Next month"
                className="flex h-6 w-6 items-center justify-center rounded-md hover:bg-black/10 dark:hover:bg-white/10 text-neutral-600 dark:text-neutral-300"
              >
                ›
              </button>
            </div>
          </div>

          {/* Days of week */}
          <div className="grid grid-cols-7 pt-2 text-center text-[10px] font-semibold text-neutral-400 dark:text-neutral-500">
            {DAYS_SHORT.map((d) => (
              <span key={d} className="py-1">
                {d}
              </span>
            ))}
          </div>

          {/* Days Grid with future limiter */}
          <div className="grid grid-cols-7 gap-1 pt-1 text-center">
            {Array.from({ length: firstDayOfMonth }).map((_, i) => (
              <span key={`empty-${i}`} />
            ))}
            {Array.from({ length: daysInMonth }).map((_, i) => {
              const day = i + 1;
              const dateObj = new Date(viewYear, viewMonth, day);
              dateObj.setHours(23, 59, 59, 999);

              const isPast = dateObj.getTime() < minDate.getTime();
              const isTooFar = dateObj.getTime() > maxDate.getTime();
              const isDisabled = isPast || isTooFar;

              const isSelected = viewYear === selYear && viewMonth === selMonth && day === selDay;

              return (
                <button
                  key={day}
                  type="button"
                  disabled={isDisabled}
                  onClick={() => handleSelectDay(day)}
                  className={`flex h-7 w-7 items-center justify-center rounded-lg text-xs font-medium transition-colors ${
                    isDisabled
                      ? 'cursor-not-allowed opacity-25 text-neutral-400'
                      : isSelected
                        ? 'bg-neutral-900 text-white font-bold shadow-sm dark:bg-white dark:text-neutral-950'
                        : 'text-neutral-800 hover:bg-black/10 dark:text-neutral-200 dark:hover:bg-white/15'
                  }`}
                >
                  {day}
                </button>
              );
            })}
          </div>

          {/* Time Picker with past hours limiter */}
          <div className="mt-3 border-t border-black/5 pt-2.5 dark:border-white/10">
            <div className="flex items-center justify-between text-[11px] font-medium text-neutral-600 dark:text-neutral-400">
              <span>Time (local)</span>
              <div className="flex items-center gap-1 font-mono">
                {/* Hour selection */}
                <select
                  value={selHours}
                  onChange={(e) => handleTimeChange(Number(e.target.value), selMinutes)}
                  aria-label="Hour"
                  className="rounded border border-black/10 bg-white/60 px-1 py-0.5 text-xs text-neutral-900 dark:border-white/15 dark:bg-black/60 dark:text-white"
                >
                  {Array.from({ length: 24 }).map((_, h) => {
                    const isToday =
                      viewYear === now.getFullYear() &&
                      viewMonth === now.getMonth() &&
                      selDay === now.getDate();
                    const isPastHour = isToday && h < now.getHours();

                    return (
                      <option key={h} value={h} disabled={isPastHour}>
                        {pad(h)}
                      </option>
                    );
                  })}
                </select>
                <span>:</span>
                {/* Minute selection */}
                <select
                  value={selMinutes}
                  onChange={(e) => handleTimeChange(selHours, Number(e.target.value))}
                  aria-label="Minute"
                  className="rounded border border-black/10 bg-white/60 px-1 py-0.5 text-xs text-neutral-900 dark:border-white/15 dark:bg-black/60 dark:text-white"
                >
                  {[0, 15, 30, 45].map((m) => (
                    <option key={m} value={m}>
                      {pad(m)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Quick Presets Bar */}
          <div className="mt-3 flex flex-wrap gap-1 border-t border-black/5 pt-2 dark:border-white/10">
            <button
              type="button"
              onClick={() => setPreset(0)}
              className="rounded-md border border-black/10 bg-white/40 px-2 py-1 text-[10px] font-medium text-neutral-700 hover:bg-black/10 dark:border-white/10 dark:bg-white/5 dark:text-neutral-300 dark:hover:bg-white/15"
            >
              Now
            </button>
            <button
              type="button"
              onClick={() => setPreset(1)}
              className="rounded-md border border-black/10 bg-white/40 px-2 py-1 text-[10px] font-medium text-neutral-700 hover:bg-black/10 dark:border-white/10 dark:bg-white/5 dark:text-neutral-300 dark:hover:bg-white/15"
            >
              +1 hr
            </button>
            <button
              type="button"
              onClick={() => setPreset(3)}
              className="rounded-md border border-black/10 bg-white/40 px-2 py-1 text-[10px] font-medium text-neutral-700 hover:bg-black/10 dark:border-white/10 dark:bg-white/5 dark:text-neutral-300 dark:hover:bg-white/15"
            >
              +3 hrs
            </button>
            <button
              type="button"
              onClick={() => setPreset(24)}
              className="rounded-md border border-black/10 bg-white/40 px-2 py-1 text-[10px] font-medium text-neutral-700 hover:bg-black/10 dark:border-white/10 dark:bg-white/5 dark:text-neutral-300 dark:hover:bg-white/15"
            >
              Tomorrow
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
