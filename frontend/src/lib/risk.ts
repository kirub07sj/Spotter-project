import type { RiskLevel } from '../api/types';

/** Single source for risk presentation (docs/04 §4). The frontend never classifies risk. */
export interface LevelMeta {
  label: string;
  icon: string;
  hex: string;
  rgb: [number, number, number];
  /** Tailwind classes for chips: dark text on light tints, white on the darkest two. */
  chip: string;
  swatch: string;
}

export const LEVEL_ORDER: readonly RiskLevel[] = ['LOW', 'MODERATE', 'HIGH', 'SEVERE', 'NO_TRAVEL'];

export const LEVELS: Record<RiskLevel, LevelMeta> = {
  LOW: {
    label: 'Low',
    icon: '●',
    hex: '#2E9E5B',
    rgb: [46, 158, 91],
    chip: 'bg-risk-low/15 text-green-900 ring-risk-low/40',
    swatch: 'bg-risk-low',
  },
  MODERATE: {
    label: 'Moderate',
    icon: '▲',
    hex: '#E3B505',
    rgb: [227, 181, 5],
    chip: 'bg-risk-moderate/20 text-yellow-900 ring-risk-moderate/50',
    swatch: 'bg-risk-moderate',
  },
  HIGH: {
    label: 'High',
    icon: '◆',
    hex: '#F08A24',
    rgb: [240, 138, 36],
    chip: 'bg-risk-high/20 text-orange-900 ring-risk-high/50',
    swatch: 'bg-risk-high',
  },
  SEVERE: {
    label: 'Severe',
    icon: '■',
    hex: '#D7263D',
    rgb: [215, 38, 61],
    chip: 'bg-risk-severe text-white ring-risk-severe',
    swatch: 'bg-risk-severe',
  },
  NO_TRAVEL: {
    label: 'No Travel',
    icon: '✕',
    hex: '#5B1A8B',
    rgb: [91, 26, 139],
    chip: 'bg-risk-notravel text-white ring-risk-notravel',
    swatch: 'bg-risk-notravel',
  },
  UNKNOWN: {
    label: 'No data',
    icon: '?',
    hex: '#9AA0A6',
    rgb: [154, 160, 166],
    chip: 'bg-risk-unknown/20 text-slate-800 ring-risk-unknown/50',
    swatch: 'bg-risk-unknown',
  },
};

export function levelIndex(level: RiskLevel): number {
  return level === 'UNKNOWN' ? -1 : LEVEL_ORDER.indexOf(level);
}

/** Heatmap colour for a continuous score 0..4 (docs/04 §4): same hues, alpha rises with risk. */
const ALPHA_STOPS = [0.1, 0.35, 0.6, 0.75, 0.75];

export function scoreColor(score: number): [number, number, number, number] {
  const s = Math.min(Math.max(score, 0), 4);
  const k = Math.min(Math.floor(s), 3);
  const f = s - k;
  const a = LEVELS[LEVEL_ORDER[k] as RiskLevel].rgb;
  const b = LEVELS[LEVEL_ORDER[k + 1] as RiskLevel].rgb;
  // Hold each band's own colour for most of the band so the map reads as discrete levels,
  // then blend quickly toward the next one near the edge.
  const t = Math.max(0, (f - 0.8) / 0.2);
  const alpha0 = ALPHA_STOPS[k] as number;
  const alpha1 = ALPHA_STOPS[k + 1] as number;
  return [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
    Math.round((alpha0 + (alpha1 - alpha0) * f) * 255),
  ];
}
