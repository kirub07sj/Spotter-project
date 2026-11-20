import { MapboxOverlay, type MapboxOverlayProps } from '@deck.gl/mapbox';
import type { PickingInfo } from '@deck.gl/core';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Map as MapGL, NavigationControl, useControl, type MapRef } from 'react-map-gl/maplibre';
import maplibregl, { type StyleSpecification } from 'maplibre-gl';
import type { Checkpoint, Plan, RouteId } from '../../api/types';
import { truckPositionAt } from '../../lib/truck';
import { useUi } from '../../store/ui';
import { useHeatmapStore } from '../heatmap';
import { heatmapLayers, truckLayers, type TruckDatum } from '../heatmap/layers';
import { endpointLayer, routeLayers } from './layers';
import { checkpointTooltip } from './tooltip';
import { FALLBACK_STYLE, MAP_STYLE_URL, US_VIEW } from './styles';
import { useMapData, type MapRoute } from './useMapData';
import { MapControls } from './MapControls';

function DeckOverlay(props: MapboxOverlayProps) {
  const overlay = useControl<MapboxOverlay>(() => new MapboxOverlay(props));
  overlay.setProps(props);
  return null;
}

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

function cameraPadding() {
  const mobile = window.innerWidth < 1024;
  return mobile
    ? { top: 80, bottom: Math.round(window.innerHeight * 0.45), left: 30, right: 30 }
    : { top: 60, bottom: 150, left: 60, right: 80 };
}

interface Props {
  plan: Plan | undefined;
  selectedId: RouteId | null;
}

export function MapView({ plan, selectedId }: Props) {
  const mapRef = useRef<MapRef>(null);
  const [style, setStyle] = useState<string | StyleSpecification>(MAP_STYLE_URL);
  const [basemapFailed, setBasemapFailed] = useState(false);
  const [labelLayerId, setLabelLayerId] = useState<string | undefined>();
  const hoveredRouteId = useUi((s) => s.hoveredRouteId);
  const hoveredCheckpoint = useUi((s) => s.hoveredCheckpoint);
  const showAllRoutes = useUi((s) => s.showAllRoutes);
  const showCheckpoints = useUi((s) => s.showCheckpoints);
  const selectRoute = useUi((s) => s.selectRoute);
  const hoverCheckpoint = useUi((s) => s.hoverCheckpoint);
  // Slider-driven state: only the map and the slider subscribe to these.
  const hour = useUi((s) => s.hour);
  const heatmapVisible = useUi((s) => s.heatmapVisible);
  const heatmapOpacity = useUi((s) => s.heatmapOpacity);
  const heatmapVersion = useHeatmapStore((s) => s.version);
  const data = useMapData(plan);
  const selected = selectedId ?? plan?.recommendation.route_id ?? 'A';
  const tSeconds = hour * 3600;

  // Camera moves only when a new plan arrives, never on slider or selection changes.
  useEffect(() => {
    if (!data?.bounds || !mapRef.current) return;
    mapRef.current.fitBounds(data.bounds, {
      padding: cameraPadding(),
      duration: prefersReducedMotion() ? 0 : 900,
      maxZoom: 10,
    });
  }, [data?.planId, data?.bounds]);

  const onStyleLoad = useCallback(() => {
    const layers = mapRef.current?.getMap().getStyle().layers ?? [];
    setLabelLayerId(layers.find((l) => l.type === 'symbol')?.id);
  }, []);

  const selectedSegments = useMemo(
    () => data?.segments.filter((s) => s.routeId === selected) ?? [],
    [data, selected],
  );

  // Nearest checkpoint to the slider time on the selected route gets a thicker ring.
  const emphasizedCheckpoint = useMemo(() => {
    const cps = data?.checkpointOffsetsS[selected];
    if (!cps?.length || tSeconds < 0 || tSeconds > (cps[cps.length - 1] as number) + 1800)
      return null;
    let best = 0;
    for (let i = 1; i < cps.length; i++) {
      if (Math.abs((cps[i] as number) - tSeconds) < Math.abs((cps[best] as number) - tSeconds))
        best = i;
    }
    return best;
  }, [data, selected, tSeconds]);

  const trucks: TruckDatum[] = data
    ? data.routes.flatMap((r) => {
        if (!showAllRoutes && r.id !== selected) return [];
        const pos = truckPositionAt(r.path, r.cumTimeS, tSeconds);
        return pos
          ? [
              {
                id: r.id,
                position: pos.position,
                selected: r.id === selected,
                moving: pos.state === 'driving',
              },
            ]
          : [];
      })
    : [];

  const heatmap = useHeatmapStore.getState();
  const showHeatmap = heatmapVisible && heatmap.bounds !== null && heatmap.planId === data?.planId;

  const layers = data
    ? [
        ...(showHeatmap && heatmap.bounds
          ? heatmapLayers({
              bitmaps: heatmap.bitmaps,
              bounds: heatmap.bounds,
              position: hour + heatmap.departureOffsetH,
              opacity: heatmapOpacity,
              beforeId: labelLayerId,
            })
          : []),
        ...routeLayers(
          data,
          {
            selectedId: selected,
            hoveredRouteId,
            hoveredCheckpoint,
            emphasizedCheckpoint,
            showAllRoutes,
            showCheckpoints,
            beforeId: labelLayerId,
          },
          selectedSegments,
        ),
        endpointLayer(data),
        ...truckLayers(trucks),
      ]
    : [];
  void heatmapVersion; // re-render when new bitmaps land (bumped at most once per frame)

  const getTooltip = useCallback(
    ({ object, layer }: PickingInfo) => {
      if (!object || !layer) return null;
      if (layer.id === 'checkpoints') {
        return { html: checkpointTooltip(object as Checkpoint, selected), style: TOOLTIP_STYLE };
      }
      if (layer.id === 'routes-unselected') {
        const r = object as MapRoute;
        return {
          text: `Route ${r.id} · ${r.label}\nClick to select`,
          style: { ...TOOLTIP_STYLE, whiteSpace: 'pre-line' },
        };
      }
      return null;
    },
    [selected],
  );

  const onHover = useCallback(
    ({ object, layer }: PickingInfo) => {
      hoverCheckpoint(layer?.id === 'checkpoints' && object ? (object as Checkpoint).index : null);
    },
    [hoverCheckpoint],
  );

  const onClick = useCallback(
    ({ object, layer }: PickingInfo) => {
      if (layer?.id === 'routes-unselected' && object) selectRoute((object as MapRoute).id);
    },
    [selectRoute],
  );

  return (
    <div className="relative h-full w-full" data-testid="map">
      <MapGL
        ref={mapRef}
        // Static import: fetched in parallel with this chunk instead of after it runs.
        mapLib={maplibregl}
        initialViewState={US_VIEW}
        mapStyle={style}
        onLoad={onStyleLoad}
        onStyleData={onStyleLoad}
        onError={(e) => {
          if (!basemapFailed && !mapRef.current?.getMap().isStyleLoaded()) {
            setBasemapFailed(true);
            setStyle(FALLBACK_STYLE);
          } else if (import.meta.env.DEV) {
            console.warn('map error', e.error);
          }
        }}
        reuseMaps
        dragRotate={false}
        style={{ width: '100%', height: '100%' }}
        attributionControl={{ compact: true }}
      >
        <NavigationControl position="top-right" showCompass={false} />
        <DeckOverlay
          interleaved
          layers={layers}
          getTooltip={getTooltip}
          onHover={onHover}
          onClick={onClick}
          getCursor={({ isHovering }) => (isHovering ? 'pointer' : 'grab')}
        />
      </MapGL>
      {basemapFailed && (
        <p className="pointer-events-none absolute left-2 top-2 rounded bg-white/90 px-2 py-1 text-xs text-slate-600 shadow">
          Basemap unavailable · routes and weather still shown
        </p>
      )}
      <MapControls />
    </div>
  );
}

const TOOLTIP_STYLE = {
  backgroundColor: 'white',
  color: '#0f172a',
  borderRadius: '8px',
  boxShadow: '0 4px 16px rgba(15,23,42,.18)',
  padding: '8px 10px',
  fontSize: '12px',
} as const;
