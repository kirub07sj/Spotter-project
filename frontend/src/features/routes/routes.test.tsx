import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useUi } from '../../store/ui';
import { planNoSafe, planOk } from '../../test/plans';
import { CheckpointTable } from './CheckpointTable';
import { RecommendationBanner } from './RecommendationBanner';
import { RouteCards } from './RouteCards';

beforeEach(() =>
  useUi.setState({ selectedRouteId: null, hoveredRouteId: null, hoveredCheckpoint: null }),
);

describe('RecommendationBanner', () => {
  it('shows the recommended route and its first reason, with all reasons behind "Why?"', async () => {
    render(<RecommendationBanner plan={planOk} />);
    const rec = planOk.recommendation;
    expect(
      screen.getByRole('heading', { name: new RegExp(`Recommended: Route ${rec.route_id}`) }),
    ).toBeVisible();
    expect(screen.getByText(rec.reasons[0] as string)).toBeVisible();
    expect(screen.queryByRole('alert')).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Why?' }));
    for (const reason of rec.reasons) expect(screen.getAllByText(reason).length).toBeGreaterThan(0);
  });

  it('uses the red variant and a simulated-weather badge for NO_SAFE_ROUTE', () => {
    render(<RecommendationBanner plan={planNoSafe} />);
    expect(screen.getByRole('alert')).toHaveTextContent('No route is safe to start at this time');
    expect(screen.getByRole('heading', { name: /Least risky: Route/ })).toBeVisible();
    expect(screen.getByText(/Simulated weather · winter storm/)).toBeVisible();
  });
});

describe('RouteCards', () => {
  it('renders a radiogroup with one card per route and marks the recommended one', () => {
    render(<RouteCards plan={planOk} selectedId={planOk.recommendation.route_id} />);
    const group = screen.getByRole('radiogroup', { name: 'Route options' });
    const cards = within(group).getAllByRole('radio');
    expect(cards).toHaveLength(planOk.routes.length);
    const selected = cards.find((c) => c.getAttribute('aria-checked') === 'true');
    expect(selected).toHaveTextContent('Recommended');
    expect(within(group).getAllByRole('img', { name: /Miles by risk level/ })).toHaveLength(3);
  });

  it('selects with click and arrow keys', async () => {
    render(<RouteCards plan={planOk} selectedId="A" />);
    await userEvent.click(screen.getByRole('radio', { name: /Route B/ }));
    expect(useUi.getState().selectedRouteId).toBe('B');
    screen.getByRole('radio', { name: /Route A/ }).focus();
    await userEvent.keyboard('{ArrowDown}');
    expect(useUi.getState().selectedRouteId).toBe('B');
    await userEvent.keyboard('{ArrowUp}{ArrowUp}');
    expect(useUi.getState().selectedRouteId).toBe('C');
  });

  it('hovering a card highlights the route on the map', async () => {
    render(<RouteCards plan={planOk} selectedId="A" />);
    await userEvent.hover(screen.getByRole('radio', { name: /Route C/ }));
    expect(useUi.getState().hoveredRouteId).toBe('C');
  });
});

describe('CheckpointTable', () => {
  it('is a real table with headers and one row per checkpoint', () => {
    const route = planNoSafe.routes[0];
    if (!route) throw new Error('fixture');
    render(<CheckpointTable route={route} />);
    const table = screen.getByRole('table');
    expect(
      within(table)
        .getAllByRole('columnheader')
        .map((h) => h.textContent),
    ).toEqual(['Mile', 'ETA', 'Wind / gust', 'Rain', 'Snow', 'Risk']);
    expect(within(table).getAllByRole('row')).toHaveLength(route.checkpoints.length + 1);
    expect(within(table).getAllByText('No Travel').length).toBeGreaterThan(0);
  });

  it('marks load-adjusted checkpoints', () => {
    const route = planNoSafe.routes.find((r) => r.checkpoints.some((c) => c.load_adjusted));
    if (!route) throw new Error('fixture has no load-adjusted checkpoint');
    render(<CheckpointTable route={route} />);
    expect(screen.getAllByText('LOAD').length).toBeGreaterThan(0);
  });

  it('virtualizes long tables', () => {
    const base = planOk.routes[0];
    if (!base) throw new Error('fixture');
    const many = Array.from({ length: 300 }, (_, i) => ({
      ...(base.checkpoints[0] as (typeof base.checkpoints)[0]),
      index: i,
      mile: i * 10,
    }));
    render(<CheckpointTable route={{ ...base, checkpoints: many }} />);
    expect(screen.getAllByRole('row').length).toBeLessThan(40);
  });
});
