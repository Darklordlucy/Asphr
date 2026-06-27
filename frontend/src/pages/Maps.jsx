import React, { useState, useCallback, useRef } from 'react';
import Navbar from '../components/Navbar';
import Map, { NavigationControl, Source, Layer, Popup } from 'react-map-gl/mapbox';
import { Layers, AlertTriangle, Car, Siren, Loader2, Star, GitFork, Cloud } from 'lucide-react';
import { fetchHazards, fetchPopularPlaces, fetchWeatherGrid, fetchHeavyTraffic } from '../services/api';

// Colour ramp by hazard score (0 → low, 1 → high)
function hazardColor(score) {
  if (score >= 0.75) return '#EF4444'; // red
  if (score >= 0.5)  return '#F97316'; // orange
  if (score >= 0.25) return '#EAB308'; // yellow
  return '#22C55E';                    // green
}

const MMR_LANDMARKS = [
  { name: 'CSMT Station Road', lat: 18.9400, lon: 72.8350 },
  { name: 'Churchgate Junction', lat: 18.9320, lon: 72.8270 },
  { name: 'Nariman Point Highway', lat: 18.9270, lon: 72.8220 },
  { name: 'Marine Lines Flyover', lat: 18.9480, lon: 72.8240 },
  { name: 'Crawford Market Area', lat: 18.9472, lon: 72.8338 },
  { name: 'Grant Road Nana Chowk', lat: 18.9610, lon: 72.8120 },
  { name: 'Byculla Bridge', lat: 18.9750, lon: 72.8330 },
  { name: 'Mumbai Central Highway', lat: 18.9720, lon: 72.8190 },
  { name: 'Haji Ali Junction', lat: 18.9790, lon: 72.8120 },
  { name: 'Lower Parel Senapati Bapat Marg', lat: 19.0010, lon: 72.8290 },
  { name: 'Worli Naka Junction', lat: 19.0020, lon: 72.8180 },
  { name: 'Shivaji Park Road', lat: 19.0260, lon: 72.8370 },
  { name: 'Dadar TT Circle', lat: 19.0178, lon: 72.8478 },
  { name: 'Prabhadevi Chowk', lat: 19.0160, lon: 72.8290 },
  { name: 'Mahim Causeway Bridge', lat: 19.0400, lon: 72.8420 },
  { name: 'Bandra Reclamation Expressway', lat: 19.0480, lon: 72.8350 },
  { name: 'BKC Avenue Road', lat: 19.0620, lon: 72.8630 },
  { name: 'Kalanagar Junction Bandra', lat: 19.0590, lon: 72.8520 },
  { name: 'LBS Marg Kurla', lat: 19.0730, lon: 72.8820 },
  { name: 'Sion Circle Flyover', lat: 19.0370, lon: 72.8590 },
  { name: 'Chembur Naka Chowk', lat: 19.0580, lon: 72.8980 },
  { name: 'SV Road Santacruz', lat: 19.0820, lon: 72.8390 },
  { name: 'WEH Vile Parle Segment', lat: 19.0980, lon: 72.8520 },
  { name: 'SV Road Andheri West', lat: 19.1190, lon: 72.8460 },
  { name: 'Andheri East MIDC Corridor', lat: 19.1200, lon: 72.8750 },
  { name: 'Powai Hiranandani Road', lat: 19.1220, lon: 72.9100 },
  { name: 'LBS Marg Ghatkopar', lat: 19.0950, lon: 72.9120 },
  { name: 'JVLR Powai Segment', lat: 19.1310, lon: 72.8900 },
  { name: 'WEH Goregaon Flyover', lat: 19.1620, lon: 72.8600 },
  { name: 'Malad Link Road Crossing', lat: 19.1850, lon: 72.8390 },
  { name: 'Kandivali Link Road', lat: 19.2060, lon: 72.8350 },
  { name: 'WEH Borivali East', lat: 19.2250, lon: 72.8620 },
  { name: 'WEH Dahisar Check Naka', lat: 19.2500, lon: 72.8600 },
  { name: 'Kanakia Road Mira Road', lat: 19.2800, lon: 72.8550 },
  { name: 'Bhayandar Station Link', lat: 19.2900, lon: 72.8450 },
  { name: 'Mulund LBS Road', lat: 19.1750, lon: 72.9480 },
  { name: 'Teen Hath Naka Thane', lat: 19.1880, lon: 72.9680 },
  { name: 'Majiwada Junction Thane', lat: 19.2150, lon: 72.9830 },
  { name: 'Ghodbunder Road Waghbil', lat: 19.2600, lon: 72.9750 },
  { name: 'Vashi Highway Segment', lat: 19.0650, lon: 72.9980 },
  { name: 'Nerul Palm Beach Road', lat: 19.0300, lon: 73.0200 },
  { name: 'Belapur Highway Junction', lat: 19.0150, lon: 73.0400 },
  { name: 'Kharghar Hiranandani Road', lat: 19.0250, lon: 73.0680 },
  { name: 'Old Panvel Highway', lat: 18.9950, lon: 73.1150 },
  { name: 'Kalamboli Circle Express Junction', lat: 19.0220, lon: 73.1050 },
  { name: 'Airoli Belapur Road', lat: 19.1550, lon: 72.9990 },
  { name: 'Kopar Khairane Link Road', lat: 19.1000, lon: 73.0100 }
];

// Generate mock MMR hazard points that cluster around real Mumbai corridors and stay on land
const mockHazards = (() => {
  const hazardTypes = [
    {
      type: 'Wet Road / Water Logging',
      descriptions: [
        'Water accumulation of 6-12 inches on the left lane of {name}. Slow-moving traffic reported.',
        'Water logging at {name} underpass. Low-clearance vehicles advised to take alternate routes.',
        'Heavy monsoon flooding near {name}. Expect delays of 15-20 minutes.'
      ]
    },
    {
      type: 'Accident Prone Zone',
      descriptions: [
        'High accident rate reported near {name} due to sharp turns and heavy merging.',
        'Frequent side-swipe collisions near {name}. Keep a safe distance from heavy vehicles.',
        'Blind spot alert near {name} exit lane. Reduce speed to 40 km/h.'
      ]
    },
    {
      type: 'Construction Obstruction',
      descriptions: [
        'Ongoing metro infrastructure construction blocking 2 lanes at {name}. Narrow road passage.',
        'Flyover construction work at {name}. Divert via secondary lanes.',
        'Road widening and barricades blocking the shoulder area at {name}.'
      ]
    },
    {
      type: 'Road Debris / Spill',
      descriptions: [
        'Reported oil/lubricant spill on {name}. High risk of vehicle skidding.',
        'Construction debris and loose gravel on the roadway near {name}. Drive slowly.',
        'Scattered metallic scrap debris on the middle lane at {name}.'
      ]
    },
    {
      type: 'Severe Pothole Area',
      descriptions: [
        'A cluster of deep potholes near {name} causing vehicle deceleration and slowdowns.',
        'Poor road surface and multiple potholes near {name}. Extreme vibration warning.',
        'Large crater-type pothole on the right lane of {name}. Hazard cone placed.'
      ]
    }
  ];

  const features = [];
  for (let i = 0; i < 60; i++) {
    const landmark = MMR_LANDMARKS[i % MMR_LANDMARKS.length];
    
    // Tiny offset (+/- 150m) to keep them strictly aligned with roads on land
    const latOffset = (Math.random() - 0.5) * 0.003;
    const lonOffset = (Math.random() - 0.5) * 0.003;
    const lat = landmark.lat + latOffset;
    const lon = landmark.lon + lonOffset;

    const hazardInfo = hazardTypes[Math.floor(Math.random() * hazardTypes.length)];
    const descTemplate = hazardInfo.descriptions[Math.floor(Math.random() * hazardInfo.descriptions.length)];
    const description = descTemplate.replace('{name}', landmark.name);

    const score = 0.35 + Math.random() * 0.63;
    let color = '#22C55E';
    if (score >= 0.75) color = '#EF4444';
    else if (score >= 0.5) color = '#F97316';
    else if (score >= 0.25) color = '#EAB308';

    features.push({
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [lon, lat]
      },
      properties: {
        id: `mock-hazard-${i}`,
        hazard_score: parseFloat(score.toFixed(2)),
        hazard_type: hazardInfo.type,
        description: description,
        color: color
      }
    });
  }

  return {
    type: 'FeatureCollection',
    features
  };
})();

const LAYERS = [
  { id: 'heavy_traffic',  label: 'Heavy Zones Traffic', icon: <Car size={18} /> },
  { id: 'popular_places', label: 'Popular Places',      icon: <Star size={18} /> },
  { id: 'hazards',        label: 'Hazards',             icon: <Siren size={18} /> },
  { id: 'road_segments',  label: 'Road Segments',       icon: <GitFork size={18} /> },
  { id: 'weather_grid',   label: 'Weather Grid',        icon: <Cloud size={18} /> },
];

const Maps = () => {
  const [activeLayer, setActiveLayer]     = useState('hazards');
  const [selectedHazard, setSelectedHazard] = useState(null);
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
    const isSegmentLayer = activeLayer === 'road_segments';
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

  const onMapClick = useCallback((event) => {
    const feature = event.features && event.features[0];
    if (feature && feature.layer.id === 'hazards-circles') {
      setSelectedHazard({
        longitude: event.lngLat.lng,
        latitude: event.lngLat.lat,
        properties: feature.properties
      });
    } else {
      setSelectedHazard(null);
    }
  }, []);

  const handleMapLoad = useCallback((e) => {
    const map = e.target;
    mapRef.current = map;
    // Tint water/background
    if (map.getLayer('background')) map.setPaintProperty('background', 'background-color', '#fef6d2');
    if (map.getLayer('water'))      map.setPaintProperty('water', 'fill-color', '#fef6d2');
    // Initial fetch for segment/hazard layers
    const isSegmentLayer = activeLayer === 'road_segments';
    if (isSegmentLayer) {
      loadHazards(map);
    }
  }, [loadHazards, activeLayer]);

  const handleMoveEnd = useCallback((e) => {
    const isSegmentLayer = activeLayer === 'road_segments';
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
    return activeLayer === 'road_segments';
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
          onClick={onMapClick}
          interactiveLayerIds={activeLayer === 'hazards' ? ['hazards-circles'] : []}
        >
          <NavigationControl position="bottom-right" />

          {selectedHazard && (
            <Popup
              longitude={selectedHazard.longitude}
              latitude={selectedHazard.latitude}
              anchor="bottom"
              onClose={() => setSelectedHazard(null)}
              closeOnClick={false}
              className="z-50"
            >
              <div className="p-3 max-w-[240px] text-black">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-3.5 h-3.5 rounded-full flex-shrink-0" style={{ backgroundColor: selectedHazard.properties.color }} />
                  <h3 className="font-bold text-sm text-gray-900 leading-tight">{selectedHazard.properties.hazard_type}</h3>
                </div>
                <p className="text-xs text-gray-700 leading-relaxed font-medium">
                  {selectedHazard.properties.description}
                </p>
                <div className="flex justify-between items-center text-[10px] text-gray-500 font-bold mt-3 pt-2 border-t border-gray-200/60">
                  <span>SEVERITY</span>
                  <span className="text-gray-900">{selectedHazard.properties.hazard_score} / 1.0</span>
                </div>
              </div>
            </Popup>
          )}

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

          {/* Road segments line layer */}
          {activeLayer === 'road_segments' && fetchedOnce && (
            <Source id="hazards" type="geojson" data={geojson}>
              <Layer
                id="hazard-lines"
                type="line"
                paint={{
                  'line-color': ['get', 'color'],
                  'line-width': 2,
                  'line-opacity': 0.85,
                }}
              />
            </Source>
          )}

          {/* Hazards mock point layer */}
          {activeLayer === 'hazards' && (
            <Source id="hazards-source" type="geojson" data={mockHazards}>
              <Layer
                id="hazards-circles"
                type="circle"
                paint={{
                  'circle-radius': 8,
                  'circle-color': ['get', 'color'],
                  'circle-stroke-width': 2,
                  'circle-stroke-color': '#FFFFFF',
                  'circle-opacity': 0.85,
                }}
              />
              <Layer
                id="hazards-labels"
                type="symbol"
                layout={{
                  'text-field': ['get', 'hazard_type'],
                  'text-size': 10,
                  'text-offset': [0, 1.2],
                  'text-anchor': 'top',
                }}
                paint={{
                  'text-color': '#1f2937',
                  'text-halo-color': '#FFFFFF',
                  'text-halo-width': 1.5,
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

                {activeLayer === 'hazards' && (
                  <>
                    <div className="flex justify-between text-[11px] font-bold text-black/60 uppercase tracking-widest">
                      <span>Hazards loaded</span>
                      <span>{mockHazards.features.length}</span>
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
