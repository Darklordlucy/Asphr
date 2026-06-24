import React, { useState, useCallback, useRef } from 'react';
import Navbar from '../components/Navbar';
import Map, { NavigationControl, Source, Layer } from 'react-map-gl/mapbox';
import { Layers, AlertTriangle, Car, Clock, Siren, Activity, Droplets, Loader2 } from 'lucide-react';
import { fetchHazards } from '../services/api';

// ── Hazard type → frontend layer id mapping ─────────────────────────────────
// The backend hazard_type field may contain these values.
// We group them under the UI layer ids so each toggle shows relevant data.
const HAZARD_TYPE_MAP = {
  potholes:      ['pothole', 'potholes', 'road_damage'],
  heavy_traffic: ['heavy_traffic', 'congestion', 'traffic'],
  rush_hour:     ['rush_hour', 'peak_hour', 'high_volume'],
  hazards:       ['hazard', 'hazards', 'accident', 'general', 'debris'],
  road_surface:  ['road_surface', 'surface_damage', 'crack'],
  waterlogging:  ['waterlogging', 'flood', 'water'],
};

// Colour ramp by hazard score (0 → low, 1 → high)
function hazardColor(score) {
  if (score >= 0.75) return '#EF4444'; // red
  if (score >= 0.5)  return '#F97316'; // orange
  if (score >= 0.25) return '#EAB308'; // yellow
  return '#22C55E';                    // green
}

const LAYERS = [
  { id: 'potholes',      label: 'Potholes',            icon: <AlertTriangle size={18} /> },
  { id: 'heavy_traffic', label: 'Heavy Zones Traffic',  icon: <Car size={18} /> },
  { id: 'rush_hour',     label: 'Rush Hr',              icon: <Clock size={18} /> },
  { id: 'hazards',       label: 'Hazards',              icon: <Siren size={18} /> },
  { id: 'road_surface',  label: 'Road Surface',         icon: <Activity size={18} /> },
  { id: 'waterlogging',  label: 'Waterlogging Risk',    icon: <Droplets size={18} /> },
];

const Maps = () => {
  const [activeLayer, setActiveLayer]   = useState('potholes');
  const [hazardData,  setHazardData]    = useState([]);   // raw backend segments
  const [loading,     setLoading]       = useState(false);
  const [error,       setError]         = useState(null);
  const [fetchedOnce, setFetchedOnce]   = useState(false);
  const mapRef = useRef(null);

  // ── Fetch hazards for current viewport ────────────────────────────────────
  const loadHazards = useCallback(async (map) => {
    const bounds = map.getBounds();
    if (!bounds) return;
    setLoading(true);
    setError(null);
    try {
      const { hazards } = await fetchHazards({
        minLat: bounds.getSouth(),
        minLon: bounds.getWest(),
        maxLat: bounds.getNorth(),
        maxLon: bounds.getEast(),
      });
      setHazardData(hazards || []);
      setFetchedOnce(true);
    } catch (e) {
      setError('Could not load road data. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleMapLoad = useCallback((e) => {
    const map = e.target;
    mapRef.current = map;
    // Tint water/background
    if (map.getLayer('background')) map.setPaintProperty('background', 'background-color', '#fef6d2');
    if (map.getLayer('water'))      map.setPaintProperty('water', 'fill-color', '#fef6d2');
    // Initial fetch
    loadHazards(map);
  }, [loadHazards]);

  const handleMoveEnd = useCallback((e) => {
    loadHazards(e.target);
  }, [loadHazards]);

  // ── Filter segments for the active UI layer ────────────────────────────────
  const allowedTypes = HAZARD_TYPE_MAP[activeLayer] || [];
  const filteredSegments = hazardData.filter((seg) => {
    const t = (seg.hazard_type || '').toLowerCase();
    // If hazard_type matches the active layer OR if it's 'unknown'/'general' and fallback layer is 'hazards'
    return allowedTypes.some((allowed) => t.includes(allowed));
  });

  // Build a single GeoJSON FeatureCollection from the filtered segments
  const geojson = {
    type: 'FeatureCollection',
    features: filteredSegments.map((seg) => ({
      type: 'Feature',
      geometry: seg.geometry,
      properties: {
        hazard_score: seg.hazard_score,
        hazard_type:  seg.hazard_type,
        color:        hazardColor(seg.hazard_score),
      },
    })),
  };

  // Count how many segments are in data (all) vs filtered
  const totalCount    = hazardData.length;
  const filteredCount = filteredSegments.length;

  return (
    <div className="h-screen w-full bg-[#fef6d2] font-sans flex flex-col relative overflow-hidden">
      <Navbar />

      {/* Map Container */}
      <div className="flex-1 relative w-full h-full">
        <Map
          ref={mapRef}
          mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
          initialViewState={{ longitude: 72.8777, latitude: 19.0760, zoom: 12 }}
          mapStyle="mapbox://styles/mapbox/light-v11"
          onLoad={handleMapLoad}
          onMoveEnd={handleMoveEnd}
        >
          <NavigationControl position="bottom-right" />

          {/* Hazard road segments layer */}
          {fetchedOnce && (
            <Source id="hazards" type="geojson" data={geojson}>
              <Layer
                id="hazard-lines"
                type="line"
                paint={{
                  'line-color': ['get', 'color'],
                  'line-width': 3,
                  'line-opacity': 0.85,
                }}
              />
            </Source>
          )}
        </Map>

        {/* Floating Data Options Panel */}
        <div className="absolute top-28 left-6 z-10 w-80 bg-[#8F9D68] backdrop-blur-xl text-black p-6 rounded-3xl shadow-[0_20px_50px_rgba(0,0,0,0.2)] border border-black/10">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Layers className="text-black" size={24} />
              <h2 className="text-xl font-bold tracking-tight">Map Data</h2>
            </div>
            {loading && <Loader2 size={18} className="animate-spin text-black/60" />}
          </div>

          {/* Layer toggles */}
          <div className="space-y-2">
            {LAYERS.map((layer) => (
              <button
                key={layer.id}
                onClick={() => setActiveLayer(layer.id)}
                className={`w-full flex items-center gap-4 p-4 rounded-2xl transition-all duration-300 font-medium text-sm border
                  ${activeLayer === layer.id
                    ? 'bg-black text-[#fef6d2] shadow-lg scale-[1.02] border-black'
                    : 'bg-[#fef6d2]/30 hover:bg-[#fef6d2]/50 text-black/80 hover:text-black border-black/5'
                  }`}
              >
                <div className={activeLayer === layer.id ? 'text-brand-yellow' : 'text-black/60'}>
                  {layer.icon}
                </div>
                <span>{layer.label}</span>
              </button>
            ))}
          </div>

          {/* Status / legend */}
          <div className="mt-8 pt-6 border-t border-black/10 space-y-3">
            {error ? (
              <p className="text-xs text-red-700 font-semibold bg-red-100 rounded-xl px-3 py-2">{error}</p>
            ) : fetchedOnce ? (
              <>
                <div className="flex justify-between text-[11px] font-bold text-black/60 uppercase tracking-widest">
                  <span>Segments loaded</span>
                  <span>{filteredCount} / {totalCount}</span>
                </div>
                {/* Colour legend */}
                <div className="flex gap-2 flex-wrap">
                  {[
                    { label: 'Low',    color: '#22C55E' },
                    { label: 'Med',    color: '#EAB308' },
                    { label: 'High',   color: '#F97316' },
                    { label: 'Severe', color: '#EF4444' },
                  ].map(({ label, color }) => (
                    <div key={label} className="flex items-center gap-1">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                      <span className="text-[10px] font-bold text-black/60">{label}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-xs text-black/80 leading-relaxed font-medium">
                Select a layer above to visualize statistical road data on the map.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Maps;
