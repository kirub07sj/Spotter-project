import type { UseQueryResult } from '@tanstack/react-query';
import { act, render, screen } from '@testing-library/react';
import { Profiler } from 'react';
import type { Plan } from '../api/types';
import { ApiError } from '../api/client';
import { useUi } from '../store/ui';
import { planOk } from '../test/plans';
import { ResultsPanel } from './ResultsPanel';

const query = (over: Partial<UseQueryResult<Plan>>) =>
  ({
    data: undefined,
    isError: false,
    error: null,
    refetch: vi.fn(),
    ...over,
  }) as unknown as UseQueryResult<Plan>;

describe('ResultsPanel', () => {
  it('does not re-render cards or the table while the slider moves (docs/04 §7)', () => {
    const onRender = vi.fn();
    render(
      <Profiler id="results" onRender={onRender}>
        <ResultsPanel query={query({ data: planOk })} submitted selectedId={null} />
      </Profiler>,
    );
    const commits = onRender.mock.calls.length;
    act(() => {
      for (let h = 0; h <= 48; h += 0.05) useUi.getState().setHour(h);
      useUi.getState().setPlaying(true);
      useUi.getState().setPlaying(false);
    });
    expect(onRender.mock.calls.length).toBe(commits);
  });

  it('shows the empty-state hint before the first plan', () => {
    render(<ResultsPanel query={query({})} submitted={false} selectedId={null} />);
    expect(screen.getByText(/compare 3 routes by weather risk/)).toBeVisible();
  });

  it('shows skeletons while loading', () => {
    const { container } = render(<ResultsPanel query={query({})} submitted selectedId={null} />);
    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
  });

  it.each([
    ['NO_ROUTE', 422, /No drivable route/],
    ['PROVIDER_UNAVAILABLE', 503, /service unavailable/],
    ['RATE_LIMITED', 429, /Too many requests/],
    ['NETWORK_ERROR', 0, /Can’t reach the server/],
  ] as const)('maps %s to a clear message with retry', (code, status, title) => {
    const refetch = vi.fn();
    render(
      <ResultsPanel
        query={query({ isError: true, error: new ApiError(code, status, 'x'), refetch })}
        submitted
        selectedId={null}
      />,
    );
    expect(screen.getByRole('alert')).toHaveTextContent(title);
    act(() => screen.getByRole('button', { name: 'Retry' }).click());
    expect(refetch).toHaveBeenCalled();
  });
});
