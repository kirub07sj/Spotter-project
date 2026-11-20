import { LEVELS, LEVEL_ORDER, levelIndex, scoreColor } from './risk';

describe('risk palette', () => {
  it('matches the documented colours (docs/04 §4)', () => {
    expect(LEVELS.LOW.hex).toBe('#2E9E5B');
    expect(LEVELS.MODERATE.hex).toBe('#E3B505');
    expect(LEVELS.HIGH.hex).toBe('#F08A24');
    expect(LEVELS.SEVERE.hex).toBe('#D7263D');
    expect(LEVELS.NO_TRAVEL.hex).toBe('#5B1A8B');
    expect(LEVELS.UNKNOWN.hex).toBe('#9AA0A6');
  });

  it('keeps rgb and hex in sync', () => {
    for (const meta of Object.values(LEVELS)) {
      const hex = `#${meta.rgb.map((c) => c.toString(16).padStart(2, '0')).join('')}`.toUpperCase();
      expect(hex).toBe(meta.hex);
    }
  });

  it('gives every level a text label and an icon, so colour never stands alone', () => {
    for (const meta of Object.values(LEVELS)) {
      expect(meta.label.length).toBeGreaterThan(0);
      expect(meta.icon.length).toBeGreaterThan(0);
    }
  });

  it('orders levels', () => {
    expect(LEVEL_ORDER.map(levelIndex)).toEqual([0, 1, 2, 3, 4]);
    expect(levelIndex('UNKNOWN')).toBe(-1);
  });

  it('heatmap alpha rises with risk and hue matches the band', () => {
    expect(scoreColor(0)).toEqual([...LEVELS.LOW.rgb, Math.round(0.1 * 255)]);
    expect(scoreColor(1)[3]).toBe(Math.round(0.35 * 255));
    expect(scoreColor(2.5).slice(0, 3)).toEqual(LEVELS.HIGH.rgb);
    expect(scoreColor(4)).toEqual([...LEVELS.NO_TRAVEL.rgb, Math.round(0.75 * 255)]);
    expect(scoreColor(9)).toEqual(scoreColor(4));
    const alphas = [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4].map((s) => scoreColor(s)[3]);
    expect([...alphas].sort((a, b) => a - b)).toEqual(alphas);
  });
});
