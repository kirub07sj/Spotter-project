import { ApiError } from '../api/client';

/** Error codes from the API mapped to what the driver should do next (docs/04 §9). */
export function errorMessage(err: unknown): { title: string; detail: string } {
  if (!(err instanceof ApiError)) {
    return { title: 'Something went wrong', detail: 'Please try again.' };
  }
  switch (err.code) {
    case 'VALIDATION_ERROR':
      return { title: 'Check the trip details', detail: err.message };
    case 'NO_ROUTE':
      return {
        title: 'No drivable route',
        detail: 'No road route connects these places. Try different points.',
      };
    case 'ROUTE_TOO_LONG':
      return {
        title: 'Trip too long',
        detail: 'Routes over 3,000 miles are not supported. Split the trip into legs.',
      };
    case 'GEOCODE_NOT_FOUND':
      return { title: 'Place not found', detail: err.message };
    case 'PROVIDER_UNAVAILABLE':
      return {
        title: 'Routing or weather service unavailable',
        detail: `${err.message} Your inputs are kept, so you can retry in a moment.`,
      };
    case 'RATE_LIMITED':
      return {
        title: 'Too many requests',
        detail: `Please wait${err.retryAfterS ? ` ${err.retryAfterS} s` : ' a moment'} and retry.`,
      };
    case 'NETWORK_ERROR':
      return { title: 'Can’t reach the server', detail: 'Check your connection and retry.' };
    default:
      return { title: 'Something went wrong', detail: err.message };
  }
}
