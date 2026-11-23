import type { Plan, RouteId } from '../../api/types';
import { ROUTE_COLORS } from '../../lib/routes';
import { useUi } from '../../store/ui';
import { CheckpointTable } from './CheckpointTable';

interface Props {
  plan: Plan | undefined;
  selectedId: RouteId | null;
}

/** Floating bottom-right checkpoint inspector panel (docs/04 §1, Stitch design). */
export function CheckpointPanel({ plan, selectedId }: Props) {
  const open = useUi((s) => s.checkpointTableOpen);
  const setOpen = useUi((s) => s.setCheckpointTableOpen);

  if (!plan || !open) return null;

  const selected = selectedId ?? plan.recommendation.route_id;
  const route = plan.routes.find((r) => r.id === selected) ?? plan.routes[0];
  if (!route) return null;

  const routeColor = ROUTE_COLORS[route.id]?.hex ?? '#3b82f6';

  return (
    <aside
      className="glass-panel pointer-events-auto absolute bottom-5 right-16 z-20 flex w-fit max-w-[calc(100vw-30rem)] max-h-[48vh] flex-col overflow-hidden max-lg:hidden"
      aria-label="Route checkpoints"
    >
      <header className="glass-header flex items-center justify-between px-4 py-2.5">
        <div className="flex items-center gap-2.5">
          <span
            className="h-2.5 w-2.5 rounded-full ring-2 ring-white/50 dark:ring-black/50"
            style={{ background: routeColor }}
            aria-hidden="true"
          />
          <div>
            <h3 className="text-xs font-bold tracking-tight text-neutral-900 dark:text-white">
              Checkpoints · Route {route.id}
            </h3>
            <p className="text-[11px] text-neutral-500 dark:text-neutral-400">
              {route.checkpoints.length} stops · every {plan.assumptions.sample_interval_mi} mi
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="ml-4 flex h-6 w-6 items-center justify-center rounded-full text-neutral-400 hover:bg-black/5 hover:text-neutral-900 dark:hover:bg-white/10 dark:hover:text-white transition-colors"
          aria-label="Close checkpoints panel"
          title="Close panel"
        >
          <span aria-hidden="true" className="text-xs font-bold leading-none">
            ✕
          </span>
        </button>
      </header>
      <div className="flex-1 overflow-y-auto overflow-x-hidden p-2.5">
        <CheckpointTable route={route} />
      </div>
    </aside>
  );
}
