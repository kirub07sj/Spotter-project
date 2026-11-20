import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { ApiError, apiFetch, postJson } from './client';
import type { Place, Plan, PlanRequest, Scenario } from './types';

export interface PlanInputs {
  request: PlanRequest;
  scenario: Scenario | null;
}

const FIVE_MINUTES = 5 * 60 * 1000;

export function usePlan(inputs: PlanInputs | null) {
  return useQuery({
    queryKey: ['plan', inputs],
    enabled: inputs !== null,
    staleTime: FIVE_MINUTES,
    retry: false,
    queryFn: ({ signal }) => {
      const query = inputs?.scenario ? `?scenario=${inputs.scenario}` : '';
      return postJson<Plan>(`/plans${query}`, inputs?.request, signal);
    },
  });
}

export function useGeocode(query: string) {
  const q = query.trim();
  return useQuery({
    queryKey: ['geocode', q.toLowerCase()],
    enabled: q.length >= 3,
    staleTime: 24 * 60 * 60 * 1000,
    placeholderData: keepPreviousData,
    retry: false,
    queryFn: async ({ signal }) => {
      try {
        const params = new URLSearchParams({ q, limit: '5' });
        const body = await apiFetch<{ results: Place[] }>(`/geocode?${params}`, { signal });
        return body.results;
      } catch (err) {
        if (err instanceof ApiError && err.code === 'GEOCODE_NOT_FOUND') return [];
        throw err;
      }
    },
  });
}
