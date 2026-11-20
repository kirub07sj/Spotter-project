import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useUi } from '../../store/ui';
import { planOk } from '../../test/plans';
import { ForecastSlider } from './ForecastSlider';
import { useHeatmapStore } from './store';

const departure = planOk.assumptions.departure_time;

beforeEach(() => {
  useUi.setState({ hour: 0, playing: false });
  useHeatmapStore.setState({ status: 'ready', ready: 49, bitmaps: new Array(49) });
});

describe('ForecastSlider', () => {
  it('keeps manual navigation available and prevents playback for reduced motion', () => {
    vi.stubGlobal('matchMedia', () => ({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
    try {
      render(<ForecastSlider departure={departure} route={planOk.routes[0]} />);
      expect(screen.getByRole('button', { name: 'Play forecast' })).toBeDisabled();
      const slider = screen.getByRole('slider');
      expect(slider).toBeEnabled();
      fireEvent.keyDown(slider, { key: 'ArrowRight' });
      expect(useUi.getState().hour).toBe(1);
      fireEvent.keyDown(slider, { key: ' ' });
      expect(useUi.getState().playing).toBe(false);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('is a native range 0-48 with spoken value text', () => {
    render(<ForecastSlider departure={departure} route={planOk.routes[0]} />);
    const slider = screen.getByRole('slider', { name: 'Forecast time' });
    expect(slider).toHaveAttribute('min', '0');
    expect(slider).toHaveAttribute('max', '48');
    expect(slider).toHaveAttribute('step', '0.05');
    expect(slider.getAttribute('aria-valuetext')).toMatch(/^Plus 0 hours, /);
    expect(screen.getByText(/^\+0h · /)).toBeVisible();
  });

  it('arrows move 1 h, Shift+arrows 6 h, Home/End jump, Space plays', async () => {
    render(<ForecastSlider departure={departure} route={planOk.routes[0]} />);
    const slider = screen.getByRole('slider', { name: 'Forecast time' });
    slider.focus();
    await userEvent.keyboard('{ArrowRight}');
    expect(useUi.getState().hour).toBe(1);
    await userEvent.keyboard('{Shift>}{ArrowRight}{/Shift}');
    expect(useUi.getState().hour).toBe(7);
    await userEvent.keyboard('{ArrowLeft}');
    expect(useUi.getState().hour).toBe(6);
    await userEvent.keyboard('{End}');
    expect(useUi.getState().hour).toBe(48);
    await userEvent.keyboard('{Home}');
    expect(useUi.getState().hour).toBe(0);
    await userEvent.keyboard(' ');
    expect(useUi.getState().playing).toBe(true);
    await userEvent.keyboard(' ');
    expect(useUi.getState().playing).toBe(false);
  });

  it('is disabled with "Loading forecast…" until the first bitmap', () => {
    useHeatmapStore.setState({ status: 'loading', ready: 0 });
    render(<ForecastSlider departure={departure} route={planOk.routes[0]} />);
    expect(screen.getByRole('slider')).toBeDisabled();
    expect(screen.getByText('Loading forecast…')).toBeVisible();
    act(() => useHeatmapStore.setState({ status: 'rendering', ready: 32, bitmaps: new Array(49) }));
    expect(screen.getByRole('slider')).toBeEnabled();
    expect(screen.getByText('rendering 32/49')).toBeVisible();
  });

  it('draws one ETA tick per checkpoint inside the 48 h window', () => {
    const route = planOk.routes[0];
    const { container } = render(<ForecastSlider departure={departure} route={route} />);
    expect(container.querySelectorAll('span.bg-slate-900.w-px').length).toBe(
      route?.checkpoints.length,
    );
  });
});
