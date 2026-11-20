import { render, screen } from '@testing-library/react';
import { App } from './App';

describe('App', () => {
  it('renders the title', () => {
    render(<App />);
    expect(screen.getByRole('heading', { name: /weather-aware truck routing/i })).toBeVisible();
  });
});
