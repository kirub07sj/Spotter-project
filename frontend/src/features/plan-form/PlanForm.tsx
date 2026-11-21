import { zodResolver } from '@hookform/resolvers/zod';
import { Controller, useForm } from 'react-hook-form';
import type { PlanInputs } from '../../api/hooks';
import { formatInt, parseLoad } from '../../lib/format';
import { Spinner } from '../../lib/ui/Spinner';
import { GeocoderInput } from './GeocoderInput';
import { nextHourLocal, planFormSchema, toPlanInputs, type PlanFormValues } from './schema';

interface Props {
  onSubmit: (inputs: PlanInputs) => void;
  loading: boolean;
  initial?: Partial<PlanFormValues>;
}

const INTERVALS = ['10', '25', '50'] as const;

export function PlanForm({ onSubmit, loading, initial }: Props) {
  const {
    control,
    register,
    handleSubmit,
    setValue,
    formState: { errors, isValid },
  } = useForm<PlanFormValues>({
    resolver: zodResolver(planFormSchema),
    mode: 'onChange',
    defaultValues: {
      origin: null,
      destination: null,
      departure: nextHourLocal(),
      load: '42,000',
      interval: '25',
      scenario: 'off',
      ...initial,
    },
  });

  return (
    <form
      className="space-y-3"
      noValidate
      aria-label="Plan a trip"
      onSubmit={handleSubmit((v) => onSubmit(toPlanInputs(v)))}
    >
      <Controller
        control={control}
        name="origin"
        render={({ field }) => (
          <GeocoderInput
            label="Origin"
            placeholder="City or address"
            value={field.value}
            onChange={field.onChange}
            error={errors.origin?.message}
            autoFocus
          />
        )}
      />
      <Controller
        control={control}
        name="destination"
        render={({ field }) => (
          <GeocoderInput
            label="Destination"
            placeholder="City or address"
            value={field.value}
            onChange={field.onChange}
            error={errors.destination?.message}
          />
        )}
      />
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label
            htmlFor="departure"
            className="mb-1 block text-xs font-medium text-neutral-600 dark:text-neutral-300"
          >
            Departure
          </label>
          <input
            id="departure"
            type="datetime-local"
            className="w-full rounded-xl border border-black/10 bg-black/[0.04] px-2.5 py-2 text-sm text-neutral-900 shadow-inner [color-scheme:light] focus:border-black/40 focus:bg-black/[0.06] focus:outline-none focus:ring-1 focus:ring-black/20 dark:border-white/10 dark:bg-white/[0.06] dark:text-white dark:[color-scheme:dark] dark:focus:border-white/40 dark:focus:bg-white/[0.1] dark:focus:ring-white/20"
            aria-invalid={Boolean(errors.departure)}
            aria-describedby={errors.departure ? 'trip-error' : undefined}
            {...register('departure')}
          />
        </div>
        <div>
          <label
            htmlFor="load"
            className="mb-1 block text-xs font-medium text-neutral-600 dark:text-neutral-300"
          >
            Load (lb)
          </label>
          <input
            id="load"
            inputMode="numeric"
            className="w-full rounded-xl border border-black/10 bg-black/[0.04] px-3 py-2 text-sm text-neutral-900 placeholder-neutral-400 shadow-inner focus:border-black/40 focus:bg-black/[0.06] focus:outline-none focus:ring-1 focus:ring-black/20 dark:border-white/10 dark:bg-white/[0.06] dark:text-white dark:placeholder-neutral-400 dark:focus:border-white/40 dark:focus:bg-white/[0.1] dark:focus:ring-white/20"
            aria-invalid={Boolean(errors.load)}
            aria-describedby={errors.load ? 'trip-error' : undefined}
            {...register('load', {
              onBlur: (e: React.FocusEvent<HTMLInputElement>) => {
                const n = parseLoad(e.target.value);
                if (n !== null) setValue('load', formatInt(n), { shouldValidate: true });
              },
            })}
          />
        </div>
      </div>
      {(errors.departure || errors.load) && (
        <p id="trip-error" role="alert" className="text-xs text-rose-600 dark:text-rose-400">
          {errors.departure?.message ?? errors.load?.message}
        </p>
      )}
      <fieldset>
        <legend className="mb-1 block text-xs font-medium text-neutral-600 dark:text-neutral-300">
          Checkpoint every
        </legend>
        <div className="grid grid-cols-3 overflow-hidden rounded-xl border border-black/10 bg-black/[0.03] text-sm shadow-inner dark:border-white/10 dark:bg-white/[0.04]">
          {INTERVALS.map((n) => (
            <label key={n} className="relative cursor-pointer text-center">
              <input type="radio" value={n} className="peer sr-only" {...register('interval')} />
              <span className="block py-1.5 text-neutral-600 transition-colors peer-checked:bg-black peer-checked:font-semibold peer-checked:text-white peer-focus-visible:ring-2 peer-focus-visible:ring-inset peer-focus-visible:ring-black/40 dark:text-neutral-300 dark:peer-checked:bg-white dark:peer-checked:text-black dark:peer-focus-visible:ring-white/50">
                {n} mi
              </span>
            </label>
          ))}
        </div>
      </fieldset>
      <details className="rounded-xl border border-dashed border-black/15 bg-black/[0.02] px-3.5 py-2.5 text-sm dark:border-white/15 dark:bg-white/[0.02]">
        <summary className="cursor-pointer text-xs font-medium text-neutral-700 transition-colors hover:text-black dark:text-neutral-300 dark:hover:text-white">
          Demo: simulated weather
        </summary>
        <label htmlFor="scenario" className="sr-only">
          Simulated weather scenario
        </label>
        <select
          id="scenario"
          className="mt-2 w-full rounded-xl border border-black/10 bg-white/95 px-3 py-2 text-sm text-neutral-900 [color-scheme:light] focus:border-black/40 focus:ring-1 focus:ring-black/20 dark:border-white/10 dark:bg-neutral-900/95 dark:text-white dark:[color-scheme:dark] dark:focus:border-white/40 dark:focus:ring-white/20"
          {...register('scenario')}
        >
          <option value="off">Off (real forecast)</option>
          <option value="winter_storm">Winter storm</option>
          <option value="high_wind">High wind</option>
        </select>
        <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
          Overlays a synthetic storm on the forecast so every risk level can be shown.
        </p>
      </details>
      <button
        type="submit"
        disabled={!isValid || loading}
        className="flex w-full items-center justify-center gap-2 rounded-xl bg-black px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-black/20 hover:bg-neutral-800 disabled:cursor-not-allowed disabled:bg-neutral-300 disabled:text-neutral-500 disabled:shadow-none dark:bg-white dark:text-black dark:shadow-white/10 dark:hover:bg-neutral-200 dark:disabled:bg-neutral-800 dark:disabled:text-neutral-500 transition-all"
      >
        {loading && <Spinner />}
        {loading ? 'Planning…' : 'Plan route'}
      </button>
    </form>
  );
}
