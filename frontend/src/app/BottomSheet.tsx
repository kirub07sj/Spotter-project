import { useRef, useState, type ReactNode } from 'react';
import { PEEK_PX, SNAPS, snapHeight, type Snap } from './sheet';

interface Props {
  snap: Snap;
  onSnap: (snap: Snap) => void;
  label: string;
  children: ReactNode;
}

/** Draggable bottom sheet with three snap points (docs/04 §2). The handle is also a button:
 * tap or Enter cycles peek -> half -> full, so it works without a pointer. */
export function BottomSheet({ snap, onSnap, label, children }: Props) {
  const [drag, setDrag] = useState<number | null>(null);
  const start = useRef<{ y: number; h: number; moved: boolean } | null>(null);
  const vh = typeof window === 'undefined' ? 800 : window.innerHeight;
  const height = drag ?? snapHeight(snap, vh);

  const onPointerDown = (e: React.PointerEvent) => {
    start.current = { y: e.clientY, h: height, moved: false };
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: React.PointerEvent) => {
    if (!start.current) return;
    const dy = start.current.y - e.clientY;
    if (Math.abs(dy) > 4) start.current.moved = true;
    if (start.current.moved) setDrag(Math.min(Math.max(start.current.h + dy, PEEK_PX), vh * 0.92));
  };
  const onPointerUp = () => {
    const s = start.current;
    start.current = null;
    if (!s) return;
    if (!s.moved) {
      onSnap(SNAPS[(SNAPS.indexOf(snap) + 1) % SNAPS.length] as Snap);
      return;
    }
    const nearest = SNAPS.reduce((best, cand) =>
      Math.abs(snapHeight(cand, vh) - height) < Math.abs(snapHeight(best, vh) - height)
        ? cand
        : best,
    );
    setDrag(null);
    onSnap(nearest);
  };

  return (
    <section
      aria-label={label}
      className="absolute inset-x-0 bottom-0 z-20 flex flex-col rounded-t-2xl bg-slate-50 shadow-[0_-8px_24px_rgba(15,23,42,.18)] motion-safe:transition-[height] motion-safe:duration-200"
      style={{ height, transitionProperty: drag === null ? undefined : 'none' }}
    >
      <button
        type="button"
        className="flex w-full shrink-0 touch-none justify-center py-2"
        aria-label={`Results panel, ${snap === 'full' ? 'expanded' : snap === 'half' ? 'half open' : 'collapsed'}. Activate to resize.`}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onSnap(SNAPS[(SNAPS.indexOf(snap) + 1) % SNAPS.length] as Snap);
          }
        }}
      >
        <span className="h-1.5 w-10 rounded-full bg-slate-300" aria-hidden="true" />
      </button>
      <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-4">{children}</div>
    </section>
  );
}
