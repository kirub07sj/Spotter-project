import type { ProblemCode } from './types';

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '/api/v1').replace(/\/$/, '');

export type ErrorCode = ProblemCode | 'NETWORK_ERROR' | 'INTERNAL_ERROR';

/** Parsed `application/problem+json`, or a network/unknown failure in the same shape. */
export class ApiError extends Error {
  readonly code: ErrorCode;
  readonly status: number;
  readonly retryAfterS: number | null;

  constructor(code: ErrorCode, status: number, message: string, retryAfterS: number | null = null) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.retryAfterS = retryAfterS;
  }
}

interface ProblemBody {
  code?: string;
  detail?: string;
  title?: string;
}

function isProblem(value: unknown): value is ProblemBody {
  return typeof value === 'object' && value !== null && 'code' in value;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { Accept: 'application/json', ...init.headers },
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err;
    throw new ApiError('NETWORK_ERROR', 0, 'Could not reach the server.');
  }
  const body: unknown = await response.json().catch(() => null);
  if (response.ok) return body as T;
  const retryAfter = Number(response.headers.get('Retry-After'));
  if (isProblem(body)) {
    throw new ApiError(
      body.code as ErrorCode,
      response.status,
      body.detail ?? body.title ?? 'Request failed.',
      Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter : null,
    );
  }
  throw new ApiError('INTERNAL_ERROR', response.status, 'The server returned an unexpected error.');
}

export function postJson<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  return apiFetch<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
}
