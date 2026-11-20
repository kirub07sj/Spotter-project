import { render, screen } from '@testing-library/react';
import { App } from './App';

vi.mock('./features/map/MapView', () => ({ MapView: () => <div data-testid="map" /> }));

describe('App', () => {
  it('renders the title, an empty-state hint and the form', () => {
    render(<App />);
    expect(screen.getByRole('heading', { name: /weather-aware truck routing/i })).toBeVisible();
    expect(screen.getByText(/enter a trip to compare 3 routes/i)).toBeVisible();
    expect(screen.getByRole('button', { name: /plan route/i })).toBeDisabled();
  });
});
