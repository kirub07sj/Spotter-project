import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { PlanInputs } from '../../api/hooks';
import { PlanForm } from './PlanForm';
import { nextHourLocal } from './schema';

const DENVER = { id: 'd', label: 'Denver, Colorado, United States', lat: 39.7392, lon: -104.9903 };
const SLC = { id: 's', label: 'Salt Lake City, Utah, United States', lat: 40.7608, lon: -111.891 };

function setup(initial = {}) {
  const onSubmit = vi.fn<(inputs: PlanInputs) => void>();
  render(
    <QueryClientProvider client={new QueryClient()}>
      <PlanForm onSubmit={onSubmit} loading={false} initial={initial} />
    </QueryClientProvider>,
  );
  return onSubmit;
}

describe('PlanForm', () => {
  it('keeps submit disabled until the form is valid', async () => {
    setup();
    expect(screen.getByRole('button', { name: 'Plan route' })).toBeDisabled();
  });

  it('submits a D-17 request with UTC departure, integer load and interval', async () => {
    const onSubmit = setup({ origin: DENVER, destination: SLC });
    const load = screen.getByLabelText('Load (lb)');
    await userEvent.clear(load);
    await userEvent.type(load, '35000');
    await userEvent.tab();
    expect(load).toHaveValue('35,000');
    await userEvent.click(screen.getByText('10 mi'));
    const submit = screen.getByRole('button', { name: 'Plan route' });
    await waitFor(() => expect(submit).toBeEnabled());
    await userEvent.click(submit);
    const inputs = onSubmit.mock.calls[0]?.[0];
    expect(inputs?.request.load_weight_lb).toBe(35_000);
    expect(inputs?.request.sample_interval_mi).toBe(10);
    expect(inputs?.request.origin).toEqual({
      lat: DENVER.lat,
      lon: DENVER.lon,
      label: DENVER.label,
    });
    expect(inputs?.request.departure_time).toBe(new Date(nextHourLocal()).toISOString());
    expect(inputs?.scenario).toBeNull();
  });

  it.each([
    ['0', /1 to 80,000/],
    ['80001', /1 to 80,000/],
    ['12.5', /whole number/],
  ])('rejects load %s', async (value, message) => {
    setup({ origin: DENVER, destination: SLC });
    const load = screen.getByLabelText('Load (lb)');
    await userEvent.clear(load);
    await userEvent.type(load, value);
    expect(await screen.findByText(message)).toBeVisible();
    expect(screen.getByRole('button', { name: 'Plan route' })).toBeDisabled();
  });

  it('rejects identical origin and destination and far-future departures', async () => {
    setup({ origin: DENVER, destination: DENVER });
    const departure = screen.getByLabelText('Departure');
    await userEvent.clear(departure);
    await userEvent.type(departure, '2099-01-01T10:00');
    expect(await screen.findByText(/at most 7 days ahead/)).toBeVisible();
    expect(screen.getByRole('button', { name: 'Plan route' })).toBeDisabled();
  });

  it('passes the simulated-weather scenario', async () => {
    const onSubmit = setup({ origin: DENVER, destination: SLC });
    await userEvent.click(screen.getByText('Demo: simulated weather'));
    await userEvent.selectOptions(screen.getByLabelText('Simulated weather scenario'), 'high_wind');
    const submit = screen.getByRole('button', { name: 'Plan route' });
    await waitFor(() => expect(submit).toBeEnabled());
    await userEvent.click(submit);
    expect(onSubmit.mock.calls[0]?.[0].scenario).toBe('high_wind');
  });
});
