import { z } from 'zod';
import type { PlanInputs } from '../../api/hooks';
import type { Scenario } from '../../api/types';
import { parseLoad } from '../../lib/format';

/** Mirrors D-17 so the form catches what the API would reject. The API stays the authority. */
export const MAX_LOAD_LB = 80_000;
const HOUR_MS = 3_600_000;
const placeSchema = z.object({
  id: z.string(),
  label: z.string(),
  lat: z.number(),
  lon: z.number(),
});

export const planFormSchema = z
  .object({
    origin: placeSchema.nullable(),
    destination: placeSchema.nullable(),
    departure: z.string().min(1, 'Choose a departure time'),
    load: z.string(),
    interval: z.enum(['10', '25', '50']),
    scenario: z.enum(['off', 'winter_storm', 'high_wind']),
  })
  .superRefine((v, ctx) => {
    if (!v.origin)
      ctx.addIssue({ code: 'custom', path: ['origin'], message: 'Choose an origin from the list' });
    if (!v.destination) {
      ctx.addIssue({
        code: 'custom',
        path: ['destination'],
        message: 'Choose a destination from the list',
      });
    }
    if (
      v.origin &&
      v.destination &&
      v.origin.lat === v.destination.lat &&
      v.origin.lon === v.destination.lon
    ) {
      ctx.addIssue({
        code: 'custom',
        path: ['destination'],
        message: 'Destination must differ from origin',
      });
    }
    const load = parseLoad(v.load);
    if (load === null || load < 1 || load > MAX_LOAD_LB) {
      ctx.addIssue({
        code: 'custom',
        path: ['load'],
        message: 'Load must be a whole number from 1 to 80,000 lb',
      });
    }
    const t = new Date(v.departure).getTime();
    const now = Date.now();
    if (Number.isNaN(t)) {
      ctx.addIssue({ code: 'custom', path: ['departure'], message: 'Choose a departure time' });
    } else if (t < now - HOUR_MS) {
      ctx.addIssue({
        code: 'custom',
        path: ['departure'],
        message: 'Departure can be at most 1 hour ago',
      });
    } else if (t > now + 7 * 24 * HOUR_MS) {
      ctx.addIssue({
        code: 'custom',
        path: ['departure'],
        message: 'Departure can be at most 7 days ahead',
      });
    }
  });

export type PlanFormValues = z.infer<typeof planFormSchema>;

/** `datetime-local` value for the next full hour in the browser's zone. */
export function nextHourLocal(now = new Date()): string {
  const d = new Date(now);
  d.setMinutes(0, 0, 0);
  d.setHours(d.getHours() + 1);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function toPlanInputs(v: PlanFormValues): PlanInputs {
  if (!v.origin || !v.destination) throw new Error('form is not valid');
  return {
    request: {
      origin: { lat: v.origin.lat, lon: v.origin.lon, label: v.origin.label },
      destination: { lat: v.destination.lat, lon: v.destination.lon, label: v.destination.label },
      departure_time: new Date(v.departure).toISOString(),
      load_weight_lb: parseLoad(v.load) ?? 0,
      sample_interval_mi: Number(v.interval) as 10 | 25 | 50,
    },
    scenario: v.scenario === 'off' ? null : (v.scenario as Scenario),
  };
}
