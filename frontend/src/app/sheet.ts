/** Bottom sheet snap points (docs/04 §2). */
export type Snap = 'peek' | 'half' | 'full';
export const SNAPS: Snap[] = ['peek', 'half', 'full'];
export const PEEK_PX = 132;

export function snapHeight(snap: Snap, viewport: number): number {
  if (snap === 'peek') return PEEK_PX;
  return Math.round(viewport * (snap === 'half' ? 0.5 : 0.88));
}
