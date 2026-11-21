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
      <div className="h-20 rounded-xl bg-black/[0.06] dark:bg-white/[0.06]" />
      {[0, 1, 2].map((i) => (
        <div key={i} className="h-28 rounded-xl bg-black/[0.06] dark:bg-white/[0.06]" />
      ))}
    </div>
  );
}

export function ResultsPanel({ query, submitted, selectedId }: Props) {
  if (!submitted) {
    return (
      <p className="rounded-xl border border-dashed border-black/15 bg-black/[0.02] p-4 text-center text-sm text-neutral-600 dark:border-white/15 dark:bg-white/[0.02] dark:text-neutral-400">
        Enter a trip to compare 3 routes by weather risk.
      </p>
    );
  }
  if (query.isError) {
    const { title, detail } = errorMessage(query.error);
    return (
      <div
        role="alert"
        className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 text-sm backdrop-blur-sm dark:bg-rose-950/40"
      >
        <p className="font-semibold text-rose-800 dark:text-rose-200">{title}</p>
        <p className="mt-0.5 text-rose-700 dark:text-rose-300">{detail}</p>
        <button
          type="button"
          onClick={() => void query.refetch()}
          className="mt-2.5 rounded-lg bg-neutral-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-black dark:bg-white dark:text-black dark:hover:bg-neutral-200 transition-colors"
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
            className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400"
          >
            Checkpoints · Route {route.id} · every {plan.assumptions.sample_interval_mi} mi
          </h3>
          <CheckpointTable route={route} />
        </section>
      )}
    </div>
  );
}
