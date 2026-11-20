import { planNoSafe } from '../../test/plans';
import { checkpointTooltip } from './tooltip';

describe('checkpointTooltip', () => {
  const cps = planNoSafe.routes.flatMap((r) => r.checkpoints);

  it('shows mile, ETA, every condition and the overall level', () => {
    const cp = cps[3];
    if (!cp) throw new Error('fixture');
    const html = checkpointTooltip(cp, 'A');
    for (const text of [
      'Route A · mile',
      'ETA',
      'Gust',
      'Sustained wind',
      'Rain',
      'Snow',
      'Overall',
    ]) {
      expect(html).toContain(text);
    }
  });

  it('adds the load-rule line only when it applied', () => {
    const adjusted = cps.find((c) => c.load_adjusted);
    const plain = cps.find((c) => !c.load_adjusted);
    if (!adjusted || !plain) throw new Error('fixture');
    expect(checkpointTooltip(adjusted, 'A')).toContain('Load rule applied');
    expect(checkpointTooltip(plain, 'A')).not.toContain('Load rule applied');
  });

  it('escapes HTML', () => {
    const cp = cps[0];
    if (!cp) throw new Error('fixture');
    expect(checkpointTooltip(cp, '<b>x</b>')).toContain('&lt;b&gt;');
  });
});
