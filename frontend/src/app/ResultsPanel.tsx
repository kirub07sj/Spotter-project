import type { UseQueryResult } from '@tanstack/react-query';
import type { Plan, RouteId } from '../api/types';
import { CheckpointTable, RecommendationBanner, RouteCards, Warnings } from '../features/routes';
import { errorMessage } from './errors';

interface Props {
  query: UseQueryResult<Plan>;
  submitted: boolean;
  selectedId: RouteId | null;
}

function Skeleton() {
  return (
    <div className="space-y-3 motion-safe:animate-pulse" aria-hidden="true">
      <div className="h-20 rounded-lg bg-slate-200" />
      {[0, 1, 2].map((i) => (
        <div key={i} className="h-28 rounded-lg bg-slate-200" />
      ))}
    </div>
  );
}

export function ResultsPanel({ query, submitted, selectedId }: Props) {
  if (!submitted) {
    return (
      <p className="rounded-lg border border-dashed border-slate-300 p-4 text-sm text-slate-600">
        Enter a trip to compare 3 routes by weather risk.
      </p>
    );
  }
  if (query.isError) {
    const { title, detail } = errorMessage(query.error);
    return (
      <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm">
        <p className="font-semibold text-red-900">{title}</p>
        <p className="mt-0.5 text-red-800">{detail}</p>
        <button
          type="button"
          onClick={() => void query.refetch()}
          className="mt-2 rounded-md bg-white px-3 py-1.5 text-xs font-semibold text-red-900 ring-1 ring-red-300 hover:bg-red-100"
        >
          Retry
        </button>
      </div>
    );
  }
  if (!query.data) {
    return (
      <div aria-busy="true" aria-live="polite">
        <span className="sr-only">Planning routes…</span>
        <Skeleton />
      </div>
    );
  }
  const plan = query.data;
  const selected = selectedId ?? plan.recommendation.route_id;
  const route = plan.routes.find((r) => r.id === selected) ?? plan.routes[0];
  return (
    <div className="space-y-3" aria-live="polite">
      <RecommendationBanner plan={plan} />
      <Warnings warnings={plan.warnings} />
      <RouteCards plan={plan} selectedId={selected} />
      {route && (
        <section aria-labelledby="cp-title">
          <h3
            id="cp-title"
            className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500"
          >
            Checkpoints · Route {route.id} · every {plan.assumptions.sample_interval_mi} mi
          </h3>
          <CheckpointTable route={route} />
        </section>
      )}
    </div>
  );
}
