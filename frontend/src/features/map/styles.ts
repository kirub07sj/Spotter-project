import type { StyleSpecification } from 'maplibre-gl';

export const DARK_MAP_STYLE_URL =
  import.meta.env.VITE_MAP_STYLE_URL ??
  'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

export const LIGHT_MAP_STYLE_URL = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';

export const MAP_STYLE_URL = DARK_MAP_STYLE_URL;

/** Used when the basemap style can't be loaded, so routes and the heatmap still render. */
export const FALLBACK_STYLE_DARK: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#090d16' } }],
};

export const FALLBACK_STYLE_LIGHT: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#e9eef2' } }],
};

export const FALLBACK_STYLE = FALLBACK_STYLE_DARK;

export const US_VIEW = { longitude: -98.5, latitude: 39.5, zoom: 3.4 };
