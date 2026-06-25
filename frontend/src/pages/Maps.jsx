import React, { useState, useCallback, useRef } from 'react';
import Navbar from '../components/Navbar';
import Map, { NavigationControl, Source, Layer } from 'react-map-gl/mapbox';
import { Layers, AlertTriangle, Car, Siren, Loader2, Star, GitFork, Cloud } from 'lucide-react';
import { fetchHazards, fetchPopularPlaces, fetchWeatherGrid, fetchHeavyTraffic } from '../services/api';

// ── Hazard type → frontend layer id mapping ─────────────────────────────────
// We group them under the UI layer ids so each toggle shows relevant data.
const HAZARD_TYPE_MAP = {
  potholes:      ['pothole', 'potholes', 'road_damage'],
  hazards:       ['hazard', 'hazards', 'accident', 'general', 'debris', 'accident_prone', 'wet_road'],
};

// Colour ramp by hazard score (0 → low, 1 → high)
function hazardColor(score) {
  if (score >= 0.75) return '#EF4444'; // red
  if (score >= 0.5)  return '#F97316'; // orange
  if (score >= 0.25) return '#EAB308'; // yellow
  return '#22C55E';                    // green
}

const LAYERS = [
  { id: 'potholes',       label: 'Potholes',            icon: <AlertTriangle size={18} /> },
  { id: 'heavy_traffic',  label: 'Heavy Zones Traffic', icon: <Car size={18} /> },
  { id: 'popular_places', label: 'Popular Places',      icon: <Star size={18} /> },
  { id: 'hazards',        label: 'Hazards',             icon: <Siren size={18} /> },
  { id: 'road_segments',  label: 'Road Segments',       icon: <GitFork size={18} /> },
  { id: 'weather_grid',   label: 'Weather Grid',        icon: <Cloud size={18} /> },
];

const Maps = () => {
  const [activeLayer, setActiveLayer]     = useState('potholes');
  const [hazardData, setHazardData]       = useState([]);   // raw backend segments
  const [popularPlaces, setPopularPlaces] = useState(null); // GeoJSON FeatureCollection
  const [weatherGrid, setWeatherGrid]     = useState(null); // GeoJSON FeatureCollection
  const [heavyTraffic, setHeavyTraffic]   = useState(null); // GeoJSON FeatureCollection
  const [loading, setLoading]             = useState(false);
  const [error, setError]                 = useState(null);
  const [fetchedOnce, setFetchedOnce]     = useState(false);
  const mapRef = useRef(null);

  // ── Fetch hazards for current viewport ────────────────────────────────────
  const loadHazards = useCallback(async (map) => {
    const bounds = map.getBounds();
    if (!bounds) return;
    const isSegmentLayer = activeLayer !== 'popular_places' && activeLayer !== 'weather_grid' && activeLayer !== 'heavy_traffic';
    if (isSegmentLayer) {
      setLoading(true);
    }
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
      if (isSegmentLayer) {
        setError('Could not load road data. Is the backend running?');
      }
    } finally {
      if (isSegmentLayer) {
        setLoading(false);
      }
    }
  }, [activeLayer]);

  // ── Fetch live heavy traffic points covering full MMR city area ───────────
  const loadHeavyTraffic = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchHeavyTraffic();
      setHeavyTraffic(data);
    } catch (err) {
      setError('Could not load heavy traffic data from database.');
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
    // Initial fetch for segment/hazard layers
    const isSegmentLayer = activeLayer !== 'popular_places' && activeLayer !== 'weather_grid' && activeLayer !== 'heavy_traffic';
    if (isSegmentLayer) {
      loadHazards(map);
    }
  }, [loadHazards, activeLayer]);

  const handleMoveEnd = useCallback((e) => {
    const isSegmentLayer = activeLayer !== 'popular_places' && activeLayer !== 'weather_grid' && activeLayer !== 'heavy_traffic';
    if (isSegmentLayer) {
      loadHazards(e.target);
    }
  }, [loadHazards, activeLayer]);

  // ── Handle custom layers fetching ─────────────────────────────────────────
  const handleLayerChange = useCallback(async (layerId) => {
    setActiveLayer(layerId);
    setError(null);

    if (layerId === 'popular_places' && !popularPlaces) {
      setLoading(true);
      try {
        const data = await fetchPopularPlaces();
        setPopularPlaces(data);
      } catch (err) {
        setError('Could not load popular places from database.');
      } finally {
        setLoading(false);
      }
    } else if (layerId === 'weather_grid' && !weatherGrid) {
      setLoading(true);
      try {
        const data = await fetchWeatherGrid();
        setWeatherGrid(data);
      } catch (err) {
        setError('Could not load weather grid from database.');
      } finally {
        setLoading(false);
      }
    } else if (layerId === 'heavy_traffic' && !heavyTraffic) {
      loadHeavyTraffic();
    }
  }, [popularPlaces, weatherGrid, heavyTraffic, loadHeavyTraffic]);

  // ── Filter segments for the active UI layer ────────────────────────────────
  const filteredSegments = hazardData.filter((seg) => {
    if (activeLayer === 'road_segments') {
      return true;
    }
    const allowedTypes = HAZARD_TYPE_MAP[activeLayer] || [];
    const t = (seg.hazard_type || '').toLowerCase();
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
        color:        activeLayer === 'road_segments' ? '#6B7280' : hazardColor(seg.hazard_score),
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

          {/* Popular Places layer */}
          {activeLayer === 'popular_places' && popularPlaces && (
            <Source id="popular-places" type="geojson" data={popularPlaces}>
              <Layer
                id="popular-places-circles"
                type="circle"
                paint={{
                  'circle-radius': 7,
                  'circle-color': '#2563EB',
                  'circle-stroke-width': 2,
                  'circle-stroke-color': '#FFFFFF',
                }}
              />
              <Layer
                id="popular-places-labels"
                type="symbol"
                layout={{
                  'text-field': ['get', 'name'],
                  'text-size': 11,
                  'text-offset': [0, 1.2],
                  'text-anchor': 'top',
                }}
                paint={{
                  'text-color': '#1E3A8A',
                  'text-halo-color': '#FFFFFF',
                  'text-halo-width': 1.5,
                }}
              />
            </Source>
          )}

          {/* Weather Grid layer */}
          {activeLayer === 'weather_grid' && weatherGrid && (
            <Source id="weather-grid" type="geojson" data={weatherGrid}>
              <Layer
                id="weather-grid-fills"
                type="fill"
                paint={{
                  'fill-color': [
                    'match',
                    ['get', 'weather_condition'],
                    'heavy rain', '#2563EB',
                    'rain', '#3B82F6',
                    'thunderstorm', '#1D4ED8',
                    'snow', '#93C5FD',
                    'clear', '#FBBF24',
                    'cloudy', '#F59E0B',
                    'mist', '#9CA3AF',
                    '#10B981'
                  ],
                  'fill-opacity': 0.35,
                  'fill-outline-color': '#1E293B',
                }}
              />
              <Layer
                id="weather-grid-labels"
                type="symbol"
                layout={{
                  'text-field': [
                    'concat',
                    ['get', 'weather_condition'],
                    '\n',
                    ['to-string', ['get', 'temperature']],
                    '°C'
                  ],
                  'text-size': 10,
                }}
                paint={{
                  'text-color': '#0F172A',
                  'text-halo-color': '#FFFFFF',
                  'text-halo-width': 1,
                }}
              />
            </Source>
          )}

          {/* Heavy Traffic points layer */}
          {activeLayer === 'heavy_traffic' && heavyTraffic && (
            <Source id="heavy-traffic" type="geojson" data={heavyTraffic}>
              <Layer
                id="heavy-traffic-points"
                type="circle"
                paint={{
                  'circle-radius': [
                    'match',
                    ['get', 'congestion_level'],
                    3, 9,
                    7
                  ],
                  'circle-color': [
                    'match',
                    ['get', 'congestion_level'],
                    3, '#EF4444',
                    '#F97316'
                  ],
                  'circle-stroke-width': 1.5,
                  'circle-stroke-color': '#FFFFFF',
                  'circle-opacity': 0.85,
                }}
              />
              <Layer
                id="heavy-traffic-labels"
                type="symbol"
                layout={{
                  'text-field': [
                    'concat',
                    ['to-string', ['coalesce', ['get', 'speed_kmh'], 0]],
                    ' km/h'
                  ],
                  'text-size': 9,
                  'text-offset': [0, 1.2],
                  'text-anchor': 'top',
                }}
                paint={{
                  'text-color': '#991B1B',
                  'text-halo-color': '#FFFFFF',
                  'text-halo-width': 1,
                }}
              />
            </Source>
          )}

          {/* Hazard/Road segments layer */}
          {activeLayer !== 'popular_places' && activeLayer !== 'weather_grid' && activeLayer !== 'heavy_traffic' && fetchedOnce && (
            <Source id="hazards" type="geojson" data={geojson}>
              <Layer
                id="hazard-lines"
                type="line"
                paint={{
                  'line-color': ['get', 'color'],
                  'line-width': activeLayer === 'road_segments' ? 2 : 4,
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
                onClick={() => handleLayerChange(layer.id)}
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
            ) : fetchedOnce || activeLayer === 'popular_places' || activeLayer === 'weather_grid' || (activeLayer === 'heavy_traffic' && heavyTraffic) ? (
              <>
                {activeLayer === 'popular_places' && popularPlaces && (
                  <>
                    <div className="flex justify-between text-[11px] font-bold text-black/60 uppercase tracking-widest">
                      <span>Places loaded</span>
                      <span>{popularPlaces.features?.length || 0}</span>
                    </div>
                    <p className="text-xs text-black/70 leading-relaxed font-medium">
                      Visualizing major Mumbai landmarks and geocoded points of interest.
                    </p>
                  </>
                )}

                {activeLayer === 'weather_grid' && weatherGrid && (
                  <>
                    <div className="flex justify-between text-[11px] font-bold text-black/60 uppercase tracking-widest">
                      <span>Grid cells loaded</span>
                      <span>{weatherGrid.features?.length || 0}</span>
                    </div>
                    <div className="flex gap-2 flex-wrap">
                      {[
                        { label: 'Clear', color: '#FBBF24' },
                        { label: 'Cloudy', color: '#F59E0B' },
                        { label: 'Rain', color: '#3B82F6' },
                        { label: 'Heavy/Storm', color: '#1D4ED8' },
                      ].map(({ label, color }) => (
                        <div key={label} className="flex items-center gap-1">
                          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                          <span className="text-[10px] font-bold text-black/60">{label}</span>
                        </div>
                      ))}
                    </div>
                  </>
                )}

                {activeLayer === 'heavy_traffic' && heavyTraffic && (
                  <>
                    <div className="flex justify-between text-[11px] font-bold text-black/60 uppercase tracking-widest">
                      <span>Traffic zones loaded</span>
                      <span>{heavyTraffic.features?.length || 0}</span>
                    </div>
                    <div className="flex gap-2 flex-wrap">
                      {[
                        { label: 'Heavy Traffic', color: '#F97316' },
                        { label: 'Severe Traffic', color: '#EF4444' },
                      ].map(({ label, color }) => (
                        <div key={label} className="flex items-center gap-1">
                          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                          <span className="text-[10px] font-bold text-black/60">{label}</span>
                        </div>
                      ))}
                    </div>
                  </>
                )}

                {activeLayer === 'road_segments' && (
                  <>
                    <div className="flex justify-between text-[11px] font-bold text-black/60 uppercase tracking-widest">
                      <span>Segments loaded</span>
                      <span>{filteredCount} / {totalCount}</span>
                    </div>
                    <p className="text-xs text-black/70 leading-relaxed font-medium">
                      Showing all base road segments intersecting the current map viewport.
                    </p>
                  </>
                )}

                {activeLayer !== 'popular_places' && activeLayer !== 'weather_grid' && activeLayer !== 'heavy_traffic' && activeLayer !== 'road_segments' && (
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
                )}
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
