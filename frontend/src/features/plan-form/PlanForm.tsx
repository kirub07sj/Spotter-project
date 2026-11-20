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
          <label htmlFor="departure" className="mb-1 block text-xs font-medium text-slate-600">
            Departure
          </label>
          <input
            id="departure"
            type="datetime-local"
            className="w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-sm shadow-sm"
            aria-invalid={Boolean(errors.departure)}
            {...register('departure')}
          />
        </div>
        <div>
          <label htmlFor="load" className="mb-1 block text-xs font-medium text-slate-600">
            Load (lb)
          </label>
          <input
            id="load"
            inputMode="numeric"
            className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm"
            aria-invalid={Boolean(errors.load)}
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
        <p className="text-xs text-red-700">{errors.departure?.message ?? errors.load?.message}</p>
      )}
      <fieldset>
        <legend className="mb-1 block text-xs font-medium text-slate-600">Checkpoint every</legend>
        <div className="grid grid-cols-3 overflow-hidden rounded-md border border-slate-300 text-sm shadow-sm">
          {INTERVALS.map((n) => (
            <label key={n} className="relative cursor-pointer text-center">
              <input type="radio" value={n} className="peer sr-only" {...register('interval')} />
              <span className="block py-1.5 text-slate-700 peer-checked:bg-slate-900 peer-checked:text-white peer-focus-visible:ring-2 peer-focus-visible:ring-inset peer-focus-visible:ring-blue-600">
                {n} mi
              </span>
            </label>
          ))}
        </div>
      </fieldset>
      <details className="rounded-md border border-dashed border-slate-300 px-3 py-2 text-sm">
        <summary className="cursor-pointer text-xs font-medium text-slate-600">
          Demo: simulated weather
        </summary>
        <label htmlFor="scenario" className="sr-only">
          Simulated weather scenario
        </label>
        <select
          id="scenario"
          className="mt-2 w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm"
          {...register('scenario')}
        >
          <option value="off">Off (real forecast)</option>
          <option value="winter_storm">Winter storm</option>
          <option value="high_wind">High wind</option>
        </select>
        <p className="mt-1 text-xs text-slate-500">
          Overlays a synthetic storm on the forecast so every risk level can be shown.
        </p>
      </details>
      <button
        type="submit"
        disabled={!isValid || loading}
        className="flex w-full items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
      >
        {loading && <Spinner />}
        {loading ? 'Planning…' : 'Plan route'}
      </button>
    </form>
  );
}
