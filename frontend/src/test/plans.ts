import type { Plan } from '../api/types';
import noSafe from './fixtures/plan-no-safe.json';
import ok from './fixtures/plan-ok.json';

/** Real responses captured from the API with PROVIDERS=fake. */
export const planOk = ok as Plan;
export const planNoSafe = noSafe as Plan;
