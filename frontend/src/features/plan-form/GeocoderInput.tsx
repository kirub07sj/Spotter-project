import { useEffect, useId, useRef, useState } from 'react';
import { useGeocode } from '../../api/hooks';
import type { Place } from '../../api/types';
import { Spinner } from '../../lib/ui/Spinner';

interface Props {
  label: string;
  value: Place | null;
  onChange: (place: Place | null) => void;
  error?: string;
  autoFocus?: boolean;
  placeholder?: string;
}

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), ms);
    return () => window.clearTimeout(id);
  }, [value, ms]);
  return debounced;
}

/** ARIA combobox. Debounced 250 ms, min 3 chars; TanStack Query aborts stale requests
 * through the fetch signal when the query key changes (docs/04 §3). */
export function GeocoderInput({ label, value, onChange, error, autoFocus, placeholder }: Props) {
  const id = useId();
  const [text, setText] = useState(value?.label ?? '');
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const blurTimerRef = useRef<number | null>(null);
  const query = useDebounced(text, 250);
  const typing = open && text !== value?.label;
  const { data: results = [], isFetching, isError } = useGeocode(typing ? query : '');

  useEffect(() => {
    return () => {
      if (blurTimerRef.current !== null) {
        window.clearTimeout(blurTimerRef.current);
      }
    };
  }, []);

  // Follow external selections (e.g. a form reset) without clobbering typed text: clearing
  // the value while typing must not wipe the input. Adjusting state during render avoids
  // an extra effect pass.
  const [lastValue, setLastValue] = useState(value);
  if (value !== lastValue) {
    setLastValue(value);
    if (value) setText(value.label);
  }

  const choose = (place: Place) => {
    onChange(place);
    setText(place.label);
    setOpen(false);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setOpen(true);
      setActive((a) => Math.min(a + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === 'Enter' && open && results[active]) {
      e.preventDefault();
      choose(results[active]);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  const showList = typing && text.trim().length >= 3;
  const listId = `${id}-list`;
  return (
    <div className="relative">
      <label
        htmlFor={id}
        className="mb-1 block text-xs font-medium text-neutral-600 dark:text-neutral-300"
      >
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={showList && results[active] ? `${id}-opt-${active}` : undefined}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-err` : undefined}
          autoComplete="off"
          autoFocus={autoFocus}
          placeholder={placeholder}
          className={`w-full rounded-xl border bg-white px-3 py-2 pr-8 text-sm text-neutral-900 placeholder-neutral-400 shadow-sm focus:border-black focus:outline-none focus:ring-1 focus:ring-black dark:border-white/10 dark:bg-white/[0.06] dark:text-white dark:placeholder-neutral-400 dark:focus:border-white/40 dark:focus:bg-white/[0.1] dark:focus:ring-white/20 ${error ? 'border-rose-500/80 ring-1 ring-rose-500/50' : 'border-neutral-300 dark:border-white/10'}`}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setOpen(true);
            setActive(0);
            if (value) onChange(null);
          }}
          onFocus={() => {
            if (blurTimerRef.current !== null) {
              window.clearTimeout(blurTimerRef.current);
            }
            setOpen(true);
          }}
          onBlur={() => {
            if (blurTimerRef.current !== null) {
              window.clearTimeout(blurTimerRef.current);
            }
            blurTimerRef.current = window.setTimeout(() => setOpen(false), 120);
          }}
          onKeyDown={onKeyDown}
        />
        {isFetching && (
          <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-neutral-400">
            <Spinner />
          </span>
        )}
      </div>
      {showList && (
        <ul
          id={listId}
          role="listbox"
          aria-label={`${label} suggestions`}
          className="glass-panel absolute z-30 mt-1.5 max-h-60 w-full overflow-auto rounded-2xl py-1 text-sm shadow-2xl"
        >
          {results.map((place, i) => (
            <li
              key={place.id}
              id={`${id}-opt-${i}`}
              role="option"
              aria-selected={i === active}
              className={`cursor-pointer px-3 py-2 transition-colors ${i === active ? 'bg-black/10 font-semibold text-black dark:bg-white/20 dark:text-white' : 'text-neutral-700 hover:bg-black/5 hover:text-black dark:text-neutral-300 dark:hover:bg-white/[0.08] dark:hover:text-white'}`}
              onMouseDown={(e) => {
                e.preventDefault();
                choose(place);
              }}
              onMouseEnter={() => setActive(i)}
            >
              {place.label}
            </li>
          ))}
          {!isFetching && results.length === 0 && (
            <li className="px-3 py-2 text-neutral-500 dark:text-neutral-400">
              {isError ? 'Search failed. Keep typing to retry.' : 'No matches'}
            </li>
          )}
        </ul>
      )}
      {error && (
        <p id={`${id}-err`} className="mt-1 text-xs text-rose-600 dark:text-rose-400">
          {error}
        </p>
      )}
    </div>
  );
}
