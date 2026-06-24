import React, { useState, useEffect, useRef } from 'react';
import Navbar from '../components/Navbar';
import Map, { NavigationControl } from 'react-map-gl/mapbox';
import { 
  MapPin, Search, Navigation, Zap, Shield, ArrowRight, Star,
  Bike, Car, Truck, Rocket, Play, Activity
} from 'lucide-react';

// --- MOCK DATA ---
const MOCK_PLACES = [
  "Bandra West, Mumbai",
  "Nariman Point, Mumbai",
  "Andheri East, Mumbai",
  "Juhu Beach, Mumbai",
  "Powai Lake, Mumbai",
  "Colaba Causeway, Mumbai",
  "Worli Sea Face, Mumbai"
];

const MOCK_ROUTE_DATA = {
  distance: "14.2 km",
  time: "45 min",
  safetyScore: 92,
  via: "via Sea Link"
};

const Routes = () => {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [originSuggestions, setOriginSuggestions] = useState([]);
  const [destSuggestions, setDestSuggestions] = useState([]);
  const [showOriginDropdown, setShowOriginDropdown] = useState(false);
  const [showDestDropdown, setShowDestDropdown] = useState(false);

  const [routeType, setRouteType] = useState('safest');
  const [vehicle, setVehicle] = useState('car');
  const [isNavigating, setIsNavigating] = useState(false);

  const originRef = useRef(null);
  const destRef = useRef(null);

  // Mock Debounced Search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (origin.length > 1) {
        setOriginSuggestions(MOCK_PLACES.filter(p => p.toLowerCase().includes(origin.toLowerCase())));
      } else {
        setOriginSuggestions([]);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [origin]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (destination.length > 1) {
        setDestSuggestions(MOCK_PLACES.filter(p => p.toLowerCase().includes(destination.toLowerCase())));
      } else {
        setDestSuggestions([]);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [destination]);

  // Click outside listener for dropdowns
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (originRef.current && !originRef.current.contains(event.target)) setShowOriginDropdown(false);
      if (destRef.current && !destRef.current.contains(event.target)) setShowDestDropdown(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleStartNavigation = () => {
    if (origin && destination) {
      setIsNavigating(true);
    }
  };

  return (
    <div className="h-screen w-full bg-[#fef6d2] font-sans flex flex-col relative overflow-hidden">
      <Navbar />
      
      {/* Map Container */}
      <div className="flex-1 relative w-full h-full">
        <Map
          mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
          initialViewState={{ longitude: 72.8777, latitude: 19.0760, zoom: 11 }}
          mapStyle="mapbox://styles/mapbox/light-v11"
          onLoad={(e) => {
            const map = e.target;
            if (map.getLayer('background')) map.setPaintProperty('background', 'background-color', '#fef6d2');
            if (map.getLayer('water')) map.setPaintProperty('water', 'fill-color', '#fef6d2');
          }}
        >
          <NavigationControl position="bottom-right" />
        </Map>

        {/* Route Planner Overlay */}
        {!isNavigating && (
          <div className="absolute top-28 left-6 z-10 w-96 bg-[#8F9D68] backdrop-blur-xl text-black p-6 rounded-3xl shadow-[0_20px_50px_rgba(0,0,0,0.2)] border border-black/10 flex flex-col max-h-[80vh]">
            
            <div className="flex items-center gap-3 mb-6 shrink-0">
              <Navigation className="text-black" size={24} />
              <h2 className="text-xl font-bold tracking-tight">Plan Route</h2>
            </div>
            
            <div className="overflow-y-auto pr-2 custom-scrollbar flex-1">
              {/* Search Bars */}
              <div className="space-y-4 relative mb-6">
                <div className="absolute left-4 top-6 bottom-6 w-0.5 bg-black/10 z-0"></div>
                
                {/* Origin Input */}
                <div className="relative z-10" ref={originRef}>
                  <div className="flex items-center gap-4 bg-[#fef6d2]/30 p-3 rounded-2xl border border-black/5 focus-within:border-black/20 focus-within:bg-[#fef6d2] transition-all">
                    <div className="w-2.5 h-2.5 rounded-full bg-black shrink-0"></div>
                    <input 
                      type="text" 
                      value={origin}
                      onChange={(e) => { setOrigin(e.target.value); setShowOriginDropdown(true); }}
                      onFocus={() => setShowOriginDropdown(true)}
                      className="bg-transparent border-none outline-none text-black w-full text-sm font-medium placeholder:text-black/50 focus:ring-0"
                      placeholder="Choose starting point..."
                    />
                  </div>
                  {/* Origin Dropdown */}
                  {showOriginDropdown && originSuggestions.length > 0 && (
                    <div className="absolute top-full left-0 right-0 mt-2 bg-[#fef6d2] rounded-xl shadow-xl border border-black/10 overflow-hidden z-50">
                      {originSuggestions.map((place, idx) => (
                        <div 
                          key={idx} 
                          className="px-4 py-3 hover:bg-black/5 cursor-pointer text-sm text-black font-medium transition-colors"
                          onClick={() => { setOrigin(place); setShowOriginDropdown(false); }}
                        >
                          {place}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Destination Input */}
                <div className="relative z-10" ref={destRef}>
                  <div className="flex items-center gap-4 bg-[#fef6d2]/30 p-3 rounded-2xl border border-black/5 focus-within:border-black/20 focus-within:bg-[#fef6d2] transition-all">
                    <MapPin className="text-red-600 shrink-0" size={16} />
                    <input 
                      type="text" 
                      value={destination}
                      onChange={(e) => { setDestination(e.target.value); setShowDestDropdown(true); }}
                      onFocus={() => setShowDestDropdown(true)}
                      className="bg-transparent border-none outline-none text-black w-full text-sm font-medium placeholder:text-black/50 focus:ring-0"
                      placeholder="Choose destination..."
                    />
                  </div>
                  {/* Dest Dropdown */}
                  {showDestDropdown && destSuggestions.length > 0 && (
                    <div className="absolute top-full left-0 right-0 mt-2 bg-[#fef6d2] rounded-xl shadow-xl border border-black/10 overflow-hidden z-50">
                      {destSuggestions.map((place, idx) => (
                        <div 
                          key={idx} 
                          className="px-4 py-3 hover:bg-black/5 cursor-pointer text-sm text-black font-medium transition-colors"
                          onClick={() => { setDestination(place); setShowDestDropdown(false); }}
                        >
                          {place}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Vehicle Selector (Horizontal Scroll) */}
              <div className="mb-6">
                <h3 className="text-xs font-bold uppercase tracking-widest text-black/50 mb-3">Vehicle</h3>
                <div className="flex gap-2 overflow-x-auto pb-2 custom-scrollbar hide-scrollbar">
                  {[
                    { id: 'bike', icon: <Bike size={16}/>, label: 'Bike' },
                    { id: 'car', icon: <Car size={16}/>, label: 'Car' },
                    { id: 'truck', icon: <Truck size={16}/>, label: 'Truck' },
                    { id: 'supercar', icon: <Rocket size={16}/>, label: 'Supercar' },
                  ].map(v => (
                    <button
                      key={v.id}
                      onClick={() => setVehicle(v.id)}
                      className={`flex flex-col items-center justify-center min-w-[72px] p-3 rounded-2xl transition-all duration-300 ${
                        vehicle === v.id ? 'bg-black text-[#fef6d2] shadow-md scale-105' : 'bg-[#fef6d2]/30 text-black/70 hover:bg-[#fef6d2]/50'
                      }`}
                    >
                      <div className="mb-1">{v.icon}</div>
                      <span className="text-[10px] font-bold">{v.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Route Type Selector (Grid) */}
              <div className="mb-6">
                <h3 className="text-xs font-bold uppercase tracking-widest text-black/50 mb-3">Route Type</h3>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: 'fastest', icon: <Zap size={16}/>, label: 'Fastest' },
                    { id: 'safest', icon: <Shield size={16}/>, label: 'Safest' },
                    { id: 'straightest', icon: <ArrowRight size={16}/>, label: 'Straightest' },
                    { id: 'popular', icon: <Star size={16}/>, label: 'Popular' },
                  ].map(rt => (
                    <button
                      key={rt.id}
                      onClick={() => setRouteType(rt.id)}
                      className={`flex items-center gap-2 p-3 rounded-2xl transition-all duration-300 ${
                        routeType === rt.id ? 'bg-brand-yellow text-black font-bold shadow-md border border-black/10' : 'bg-[#fef6d2]/30 text-black/80 hover:bg-[#fef6d2]/50 font-medium border border-transparent'
                      }`}
                    >
                      <div className={routeType === rt.id ? 'text-black' : 'text-black/60'}>{rt.icon}</div>
                      <span className="text-xs">{rt.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Route Summary Panel */}
              {origin && destination && (
                <div className="bg-[#fef6d2]/30 p-4 rounded-2xl mb-6 border border-black/5">
                  <div className="flex justify-between items-end mb-4">
                    <div>
                      <div className="text-3xl font-black text-black tracking-tighter leading-none">{MOCK_ROUTE_DATA.time}</div>
                      <div className="text-xs font-bold text-black/60 uppercase tracking-wide mt-1">{MOCK_ROUTE_DATA.distance} • {MOCK_ROUTE_DATA.via}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-xl font-black text-green-700">{MOCK_ROUTE_DATA.safetyScore}</div>
                      <div className="text-[10px] font-bold text-black/50 uppercase tracking-wider">Safety Score</div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Start Navigation Button */}
            <button 
              onClick={handleStartNavigation}
              disabled={!origin || !destination}
              className={`w-full mt-2 py-4 rounded-2xl flex items-center justify-center gap-2 transition-all duration-300 font-bold shrink-0
                ${origin && destination 
                  ? 'bg-black hover:bg-black/80 text-[#fef6d2] shadow-xl hover:shadow-2xl hover:-translate-y-0.5' 
                  : 'bg-black/10 text-black/30 cursor-not-allowed'
                }
              `}
            >
              <Play size={18} className={origin && destination ? "fill-[#fef6d2]" : ""} />
              Start Navigation
            </button>
          </div>
        )}

        {/* Navigation Mode Overlay (Simulated) */}
        {isNavigating && (
          <div className="absolute top-28 left-6 z-10 w-80 bg-brand-dark/90 backdrop-blur-xl text-white p-6 rounded-3xl shadow-2xl border border-white/10 flex flex-col">
            <div className="flex items-center gap-3 mb-6">
              <Activity className="text-brand-yellow animate-pulse" size={24} />
              <div>
                <h2 className="text-xl font-bold tracking-tight">Navigating</h2>
                <p className="text-xs text-white/50">{MOCK_ROUTE_DATA.time} remaining</p>
              </div>
            </div>
            
            <div className="bg-white/5 p-4 rounded-2xl mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-brand-yellow/20 flex items-center justify-center shrink-0">
                  <ArrowRight className="text-brand-yellow" size={20} />
                </div>
                <div>
                  <div className="font-bold text-lg">Continue straight</div>
                  <div className="text-sm text-white/60">on Western Express Hwy</div>
                </div>
              </div>
            </div>

            <button 
              onClick={() => setIsNavigating(false)}
              className="w-full bg-red-500 hover:bg-red-600 text-white font-bold py-3 rounded-xl transition-colors"
            >
              End Navigation
            </button>
          </div>
        )}

      </div>
      <style dangerouslySetInnerHTML={{__html: `
        .hide-scrollbar::-webkit-scrollbar {
          display: none;
        }
        .hide-scrollbar {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(0,0,0,0.1);
          border-radius: 10px;
        }
      `}} />
    </div>
  );
};

export default Routes;
