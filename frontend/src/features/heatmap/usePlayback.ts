import { useEffect } from 'react';
import { MAX_HOUR, useUi } from '../../store/ui';

const HOURS_PER_SECOND = 2;

/** requestAnimationFrame playback: advances 2 forecast hours per second, stops at +48h. */
export function usePlayback() {
  const playing = useUi((s) => s.playing);
  useEffect(() => {
    if (!playing) return;
    let last = performance.now();
    let frame = requestAnimationFrame(function tick(now) {
      const { hour, setHour, setPlaying } = useUi.getState();
      const next = hour + ((now - last) / 1000) * HOURS_PER_SECOND;
      last = now;
      if (next >= MAX_HOUR) {
        setHour(MAX_HOUR);
        setPlaying(false);
        return;
      }
      setHour(next);
      frame = requestAnimationFrame(tick);
    });
    return () => cancelAnimationFrame(frame);
  }, [playing]);
}
