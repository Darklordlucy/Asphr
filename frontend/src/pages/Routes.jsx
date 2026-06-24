import React, { useState, useEffect, useRef, useCallback } from 'react';
import Navbar from '../components/Navbar';
import Map, { NavigationControl, Source, Layer, Marker } from 'react-map-gl/mapbox';
import {
  MapPin, Navigation, Zap, Shield, ArrowRight, Star,
  Bike, Car, Truck, Rocket, Play, Activity, Loader2, AlertTriangle, X
} from 'lucide-react';
import { computeRoute } from '../services/api';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN;

// ── Mapbox Geocoding Autocomplete ────────────────────────────────────────────
async function geocodeSearch(query) {
  if (!query || query.trim().length < 3) return [];
  const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(query)}.json?access_token=${MAPBOX_TOKEN}&country=IN&proximity=72.8777,19.0760&limit=5`;
  try {
    const res = await fetch(url);
    const data = await res.json();
    return (data.features || []).map((f) => ({
      name: f.place_name,
      lat:  f.center[1],
      lon:  f.center[0],
    }));
  } catch {
    return [];
  }
}

const Routes = () => {
  // ── Search state ────────────────────────────────────────────────────────
  const [originText,         setOriginText]         = useState('');
  const [destText,           setDestText]           = useState('');
  const [originCoords,       setOriginCoords]       = useState(null); // { lat, lon }
  const [destCoords,         setDestCoords]         = useState(null);
  const [originSuggestions,  setOriginSuggestions]  = useState([]);
  const [destSuggestions,    setDestSuggestions]    = useState([]);
  const [showOriginDrop,     setShowOriginDrop]     = useState(false);
  const [showDestDrop,       setShowDestDrop]       = useState(false);

  // ── Selectors ────────────────────────────────────────────────────────────
  const [vehicle,    setVehicle]    = useState('car');
  const [routeType,  setRouteType]  = useState('fastest');

  // ── Route result ─────────────────────────────────────────────────────────
  const [routeResult,   setRouteResult]   = useState(null);
  const [routeError,    setRouteError]    = useState(null);
  const [loading,       setLoading]       = useState(false);
  const [isNavigating,  setIsNavigating]  = useState(false);

  // ── Refs ─────────────────────────────────────────────────────────────────
  const originRef      = useRef(null);
  const destRef        = useRef(null);
  const originTimer    = useRef(null);
  const destTimer      = useRef(null);

  // ── Debounced autocomplete ───────────────────────────────────────────────
  const handleOriginChange = (val) => {
    setOriginText(val);
    setOriginCoords(null);   // invalidate coords when text changes
    setRouteResult(null);
    clearTimeout(originTimer.current);
    if (val.trim().length >= 3) {
      originTimer.current = setTimeout(async () => {
        const sugs = await geocodeSearch(val);
        setOriginSuggestions(sugs);
        setShowOriginDrop(true);
      }, 300);
    } else {
      setOriginSuggestions([]);
      setShowOriginDrop(false);
    }
  };

  const handleDestChange = (val) => {
    setDestText(val);
    setDestCoords(null);
    setRouteResult(null);
    clearTimeout(destTimer.current);
    if (val.trim().length >= 3) {
      destTimer.current = setTimeout(async () => {
        const sugs = await geocodeSearch(val);
        setDestSuggestions(sugs);
        setShowDestDrop(true);
      }, 300);
    } else {
      setDestSuggestions([]);
      setShowDestDrop(false);
    }
  };

  const selectOrigin = (suggestion) => {
    setOriginText(suggestion.name);
    setOriginCoords({ lat: suggestion.lat, lon: suggestion.lon });
    setShowOriginDrop(false);
  };

  const selectDest = (suggestion) => {
    setDestText(suggestion.name);
    setDestCoords({ lat: suggestion.lat, lon: suggestion.lon });
    setShowDestDrop(false);
  };

  // ── Close dropdowns on outside click ────────────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      if (originRef.current && !originRef.current.contains(e.target)) setShowOriginDrop(false);
      if (destRef.current   && !destRef.current.contains(e.target))   setShowDestDrop(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // ── Compute route when both coords exist (or when type/vehicle changes) ─
  const canCompute = originCoords && destCoords;

  const doComputeRoute = useCallback(async () => {
    if (!canCompute) return;
    setLoading(true);
    setRouteError(null);   // always clear before new attempt
    setRouteResult(null);
    try {
      const result = await computeRoute({
        origin:       { lat: originCoords.lat, lon: originCoords.lon },
        destination:  { lat: destCoords.lat,   lon: destCoords.lon   },
        route_type:   routeType,
        vehicle_type: vehicle,
        avoid_tolls:  false,
      });
      setRouteResult(result);
      setRouteError(null); // ensure cleared on success
    } catch (e) {
      const msg = e.message || '';
      // Friendly message for known backend errors
      if (msg.includes('No routing path') || msg.includes('too close')) {
        setRouteError('No path found between these locations. Try different points.');
      } else if (msg.includes('400')) {
        setRouteError('Could not calculate route. Try selecting different start/end points.');
      } else {
        setRouteError(msg || 'Route computation failed. Is the backend running?');
      }
    } finally {
      setLoading(false);
    }
  }, [canCompute, originCoords, destCoords, routeType, vehicle]);

  // Re-fetch when routeType or vehicle changes — only if both coords are confirmed
  useEffect(() => {
    if (originCoords && destCoords) doComputeRoute();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routeType, vehicle]);

  // ── GeoJSON for the route line ────────────────────────────────────────────
  const routeGeoJSON = routeResult
    ? {
        type: 'FeatureCollection',
        features: [{
          type: 'Feature',
          geometry: routeResult.geometry,
          properties: {},
        }],
      }
    : null;

  // ── Formatted helpers ─────────────────────────────────────────────────────
  const formatDuration = (mins) => {
    if (!mins) return '—';
    const h = Math.floor(mins / 60);
    const m = Math.round(mins % 60);
    return h > 0 ? `${h}h ${m}m` : `${m} min`;
  };

  const formatDistance = (km) => {
    if (!km) return '—';
    return `${km.toFixed(1)} km`;
  };

  const safetyPercent = routeResult
    ? Math.round((1 - (routeResult.hazard_score_avg ?? 0)) * 100)
    : null;

  return (
    <div className="h-screen w-full bg-[#fef6d2] font-sans flex flex-col relative overflow-hidden">
      <Navbar />

      {/* Map */}
      <div className="flex-1 relative w-full h-full">
        <Map
          mapboxAccessToken={MAPBOX_TOKEN}
          initialViewState={{ longitude: 72.8777, latitude: 19.0760, zoom: 11 }}
          mapStyle="mapbox://styles/mapbox/light-v11"
          onLoad={(e) => {
            const map = e.target;
            if (map.getLayer('background')) map.setPaintProperty('background', 'background-color', '#fef6d2');
            if (map.getLayer('water'))      map.setPaintProperty('water', 'fill-color', '#fef6d2');
          }}
        >
          <NavigationControl position="bottom-right" />

          {/* Route line */}
          {routeGeoJSON && (
            <Source id="route" type="geojson" data={routeGeoJSON}>
              {/* Shadow / casing */}
              <Layer
                id="route-casing"
                type="line"
                paint={{ 'line-color': '#000', 'line-width': 7, 'line-opacity': 0.15 }}
                layout={{ 'line-join': 'round', 'line-cap': 'round' }}
              />
              {/* Main route */}
              <Layer
                id="route-line"
                type="line"
                paint={{ 'line-color': '#8F9D68', 'line-width': 5, 'line-opacity': 1 }}
                layout={{ 'line-join': 'round', 'line-cap': 'round' }}
              />
            </Source>
          )}

          {/* Origin marker */}
          {originCoords && (
            <Marker longitude={originCoords.lon} latitude={originCoords.lat} anchor="bottom">
              <div className="flex flex-col items-center">
                <div className="w-4 h-4 rounded-full bg-black border-2 border-white shadow-lg" />
                <div className="w-0.5 h-3 bg-black/40" />
              </div>
            </Marker>
          )}

          {/* Destination marker */}
          {destCoords && (
            <Marker longitude={destCoords.lon} latitude={destCoords.lat} anchor="bottom">
              <div className="flex flex-col items-center">
                <div
                  className="shadow-xl"
                  style={{
                    width: 28, height: 36,
                    background: '#EF4444',
                    borderRadius: '50% 50% 50% 0',
                    transform: 'rotate(-45deg)',
                    border: '2.5px solid white',
                  }}
                />
              </div>
            </Marker>
          )}
        </Map>

        {/* ── Route Planner Overlay ────────────────────────────────────────── */}
        {!isNavigating && (
          <div className="absolute top-28 left-6 z-10 w-96 bg-[#8F9D68] backdrop-blur-xl text-black p-6 rounded-3xl shadow-[0_20px_50px_rgba(0,0,0,0.2)] border border-black/10 flex flex-col max-h-[85vh]">

            {/* Header */}
            <div className="flex items-center justify-between mb-6 shrink-0">
              <div className="flex items-center gap-3">
                <Navigation className="text-black" size={24} />
                <h2 className="text-xl font-bold tracking-tight">Plan Route</h2>
              </div>
              {loading && <Loader2 size={18} className="animate-spin text-black/60" />}
            </div>

            <div className="overflow-y-auto pr-1 flex-1 space-y-5" style={{ scrollbarWidth: 'none' }}>

              {/* ── Search bars ──────────────────────────────────────────── */}
              <div className="space-y-3 relative">
                <div className="absolute left-3.5 top-7 bottom-7 w-0.5 bg-black/10 z-0" />

                {/* Origin */}
                <div className="relative z-10" ref={originRef}>
                  <div className={`flex items-center gap-3 bg-[#fef6d2]/30 p-3 rounded-2xl border transition-all
                    ${showOriginDrop ? 'border-black/30 bg-[#fef6d2]/60' : 'border-black/5'}`}
                  >
                    <div className="w-2.5 h-2.5 rounded-full bg-black shrink-0" />
                    <input
                      type="text"
                      value={originText}
                      onChange={(e) => handleOriginChange(e.target.value)}
                      onFocus={() => originSuggestions.length && setShowOriginDrop(true)}
                      className="bg-transparent border-none outline-none text-black w-full text-sm font-medium placeholder:text-black/50 focus:ring-0"
                      placeholder="Choose starting point..."
                    />
                    {originText && (
                      <button onClick={() => { setOriginText(''); setOriginCoords(null); setRouteResult(null); }}>
                        <X size={14} className="text-black/40 hover:text-black" />
                      </button>
                    )}
                  </div>
                  {showOriginDrop && originSuggestions.length > 0 && (
                    <div className="absolute top-full left-0 right-0 mt-2 bg-[#fef6d2] rounded-xl shadow-xl border border-black/10 overflow-hidden z-50">
                      {originSuggestions.map((s, i) => (
                        <div
                          key={i}
                          className="px-4 py-3 hover:bg-black/5 cursor-pointer text-sm text-black font-medium transition-colors border-b border-black/5 last:border-0"
                          onMouseDown={() => selectOrigin(s)}
                        >
                          <MapPin size={12} className="inline mr-2 text-black/40" />
                          {s.name}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Destination */}
                <div className="relative z-10" ref={destRef}>
                  <div className={`flex items-center gap-3 bg-[#fef6d2]/30 p-3 rounded-2xl border transition-all
                    ${showDestDrop ? 'border-black/30 bg-[#fef6d2]/60' : 'border-black/5'}`}
                  >
                    <MapPin className="text-red-600 shrink-0" size={16} />
                    <input
                      type="text"
                      value={destText}
                      onChange={(e) => handleDestChange(e.target.value)}
                      onFocus={() => destSuggestions.length && setShowDestDrop(true)}
                      className="bg-transparent border-none outline-none text-black w-full text-sm font-medium placeholder:text-black/50 focus:ring-0"
                      placeholder="Choose destination..."
                    />
                    {destText && (
                      <button onClick={() => { setDestText(''); setDestCoords(null); setRouteResult(null); }}>
                        <X size={14} className="text-black/40 hover:text-black" />
                      </button>
                    )}
                  </div>
                  {showDestDrop && destSuggestions.length > 0 && (
                    <div className="absolute top-full left-0 right-0 mt-2 bg-[#fef6d2] rounded-xl shadow-xl border border-black/10 overflow-hidden z-50">
                      {destSuggestions.map((s, i) => (
                        <div
                          key={i}
                          className="px-4 py-3 hover:bg-black/5 cursor-pointer text-sm text-black font-medium transition-colors border-b border-black/5 last:border-0"
                          onMouseDown={() => selectDest(s)}
                        >
                          <MapPin size={12} className="inline mr-2 text-black/40" />
                          {s.name}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* ── Vehicle Selector ─────────────────────────────────────── */}
              <div>
                <h3 className="text-xs font-bold uppercase tracking-widest text-black/50 mb-3">Vehicle</h3>
                <div className="flex gap-2 overflow-x-auto pb-1" style={{ scrollbarWidth: 'none' }}>
                  {[
                    { id: 'bike',     icon: <Bike size={16} />,   label: 'Bike'     },
                    { id: 'car',      icon: <Car size={16} />,    label: 'Car'      },
                    { id: 'truck',    icon: <Truck size={16} />,  label: 'Truck'    },
                    { id: 'supercar', icon: <Rocket size={16} />, label: 'Supercar' },
                  ].map((v) => (
                    <button
                      key={v.id}
                      onClick={() => setVehicle(v.id)}
                      className={`flex flex-col items-center justify-center min-w-[72px] p-3 rounded-2xl transition-all duration-300 ${
                        vehicle === v.id
                          ? 'bg-black text-[#fef6d2] shadow-md scale-105'
                          : 'bg-[#fef6d2]/30 text-black/70 hover:bg-[#fef6d2]/50'
                      }`}
                    >
                      <div className="mb-1">{v.icon}</div>
                      <span className="text-[10px] font-bold">{v.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* ── Route Type Selector ──────────────────────────────────── */}
              <div>
                <h3 className="text-xs font-bold uppercase tracking-widest text-black/50 mb-3">Route Type</h3>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: 'fastest',     icon: <Zap size={16} />,        label: 'Fastest'     },
                    { id: 'safest',      icon: <Shield size={16} />,     label: 'Safest'      },
                    { id: 'straightest', icon: <ArrowRight size={16} />, label: 'Straightest' },
                    { id: 'popular',     icon: <Star size={16} />,       label: 'Popular'     },
                  ].map((rt) => (
                    <button
                      key={rt.id}
                      onClick={() => setRouteType(rt.id)}
                      className={`flex items-center gap-2 p-3 rounded-2xl transition-all duration-300 ${
                        routeType === rt.id
                          ? 'bg-brand-yellow text-black font-bold shadow-md border border-black/10'
                          : 'bg-[#fef6d2]/30 text-black/80 hover:bg-[#fef6d2]/50 font-medium border border-transparent'
                      }`}
                    >
                      <div className={routeType === rt.id ? 'text-black' : 'text-black/60'}>{rt.icon}</div>
                      <span className="text-xs">{rt.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* ── Route error ──────────────────────────────────────────── */}
              {routeError && (
                <div className="flex items-start gap-2 bg-red-100 text-red-800 text-xs font-semibold p-3 rounded-2xl">
                  <AlertTriangle size={14} className="shrink-0 mt-0.5" />
                  {routeError}
                </div>
              )}

              {/* ── Route Summary ─────────────────────────────────────────── */}
              {routeResult && (
                <div className="bg-[#fef6d2]/50 p-4 rounded-2xl border border-black/5 space-y-3">
                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div>
                      <p className="text-2xl font-black text-black leading-none">
                        {formatDuration(routeResult.duration_min)}
                      </p>
                      <p className="text-[10px] font-bold text-black/50 uppercase tracking-widest mt-1">Duration</p>
                    </div>
                    <div>
                      <p className="text-2xl font-black text-black leading-none">
                        {formatDistance(routeResult.distance_km)}
                      </p>
                      <p className="text-[10px] font-bold text-black/50 uppercase tracking-widest mt-1">Distance</p>
                    </div>
                    <div>
                      <p className="text-2xl font-black text-green-700 leading-none">{safetyPercent}%</p>
                      <p className="text-[10px] font-bold text-black/50 uppercase tracking-widest mt-1">Safety</p>
                    </div>
                  </div>

                  {/* Weather alerts */}
                  {routeResult.weather_alerts?.length > 0 && (
                    <div className="text-xs text-black/70 font-medium bg-black/5 rounded-xl px-3 py-2">
                      {routeResult.weather_alerts[0]}
                    </div>
                  )}
                </div>
              )}

              {/* ── Compute button ───────────────────────────────────────── */}
              {!routeResult && canCompute && !loading && (
                <button
                  onClick={doComputeRoute}
                  className="w-full py-3 rounded-2xl bg-black text-[#fef6d2] font-bold text-sm flex items-center justify-center gap-2 hover:bg-black/80 transition-colors"
                >
                  <Zap size={16} className="fill-brand-yellow text-brand-yellow" />
                  Calculate Route
                </button>
              )}
            </div>

            {/* ── Start Navigation Button ───────────────────────────────── */}
            <button
              onClick={() => { if (routeResult) setIsNavigating(true); }}
              disabled={!routeResult || loading}
              className={`w-full mt-4 py-4 rounded-2xl flex items-center justify-center gap-2 transition-all duration-300 font-bold shrink-0
                ${routeResult && !loading
                  ? 'bg-black hover:bg-black/80 text-[#fef6d2] shadow-xl hover:shadow-2xl hover:-translate-y-0.5'
                  : 'bg-black/10 text-black/30 cursor-not-allowed'
                }
              `}
            >
              {loading
                ? <><Loader2 size={18} className="animate-spin" /> Calculating...</>
                : <><Play size={18} className={routeResult ? 'fill-[#fef6d2]' : ''} /> Start Navigation</>
              }
            </button>
          </div>
        )}

        {/* ── Navigation Mode Overlay ──────────────────────────────────────── */}
        {isNavigating && routeResult && (
          <div className="absolute top-28 left-6 z-10 w-80 bg-[#8F9D68] backdrop-blur-xl text-black p-6 rounded-3xl shadow-2xl border border-black/10 flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <Activity className="text-brand-yellow animate-pulse" size={24} />
              <div>
                <h2 className="text-xl font-bold tracking-tight">Navigating</h2>
                <p className="text-xs text-black/60">{formatDuration(routeResult.duration_min)} remaining</p>
              </div>
            </div>

            {/* First instruction */}
            {routeResult.instructions?.[0] && (
              <div className="bg-[#fef6d2]/30 p-4 rounded-2xl flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-black flex items-center justify-center shrink-0">
                  <ArrowRight className="text-brand-yellow" size={20} />
                </div>
                <div>
                  <div className="font-bold">{routeResult.instructions[0].instruction}</div>
                  {routeResult.instructions[0].distance_meters > 0 && (
                    <div className="text-xs text-black/60 mt-0.5">
                      in {routeResult.instructions[0].distance_meters}m
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Stats during nav */}
            <div className="grid grid-cols-2 gap-3 text-center">
              <div className="bg-[#fef6d2]/30 p-3 rounded-2xl">
                <p className="text-lg font-black">{formatDistance(routeResult.distance_km)}</p>
                <p className="text-[10px] font-bold text-black/50 uppercase tracking-widest">Distance</p>
              </div>
              <div className="bg-[#fef6d2]/30 p-3 rounded-2xl">
                <p className="text-lg font-black text-green-700">{safetyPercent}%</p>
                <p className="text-[10px] font-bold text-black/50 uppercase tracking-widest">Safety</p>
              </div>
            </div>

            {routeResult.weather_alerts?.[0] && (
              <p className="text-xs font-medium text-black/70 bg-black/5 rounded-xl px-3 py-2">
                {routeResult.weather_alerts[0]}
              </p>
            )}

            <button
              onClick={() => setIsNavigating(false)}
              className="w-full bg-red-500 hover:bg-red-600 text-white font-bold py-3 rounded-xl transition-colors"
            >
              End Navigation
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Routes;
