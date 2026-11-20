import {
  formatDuration,
  formatMiles,
  formatOffset,
  formatTime,
  parseLoad,
  spokenOffset,
} from './format';

describe('format', () => {
  it('formats durations as "8h 06m" and short trips in minutes', () => {
    expect(formatDuration(29_160)).toBe('8h 06m');
    expect(formatDuration(45 * 60)).toBe('45 min');
    expect(formatDuration(3600)).toBe('1h 00m');
  });

  it('formats miles', () => {
    expect(formatMiles(525.4)).toBe('525 mi');
    expect(formatMiles(25)).toBe('25.0 mi');
  });

  it('formats times as "Thu 14:20 <zone>" in the browser zone', () => {
    expect(formatTime('2026-11-19T14:20:00Z')).toMatch(/^Thu \d{2}:\d{2} \S+$/);
  });

  it('parses loads with thousands separators', () => {
    expect(parseLoad('42,000')).toBe(42_000);
    expect(parseLoad(' 80 000 ')).toBe(80_000);
    expect(parseLoad('4.5')).toBeNull();
    expect(parseLoad('')).toBeNull();
  });

  it('labels slider offsets with both offset and clock time (D-14)', () => {
    expect(formatOffset(12, '2026-11-20T02:00:00Z')).toMatch(/^\+12h · Fri \d{2}:00 /);
    expect(spokenOffset(12, '2026-11-20T02:00:00Z')).toMatch(/^Plus 12 hours, Friday/);
  });
});
