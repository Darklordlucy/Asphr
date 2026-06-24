import React, { useState } from 'react';
import Navbar from '../components/Navbar';
import Map, { NavigationControl } from 'react-map-gl/mapbox';
import { Layers, AlertTriangle, Car, Clock, Siren, Activity, Droplets } from 'lucide-react';

const Maps = () => {
  const [activeLayer, setActiveLayer] = useState('potholes');

  const layers = [
    { id: 'potholes', label: 'Potholes', icon: <AlertTriangle size={18} /> },
    { id: 'heavy_traffic', label: 'Heavy Zones Traffic', icon: <Car size={18} /> },
    { id: 'rush_hour', label: 'Rush Hr', icon: <Clock size={18} /> },
    { id: 'hazards', label: 'Hazards', icon: <Siren size={18} /> },
    { id: 'road_surface', label: 'Road Surface', icon: <Activity size={18} /> },
    { id: 'waterlogging', label: 'Waterlogging Risk', icon: <Droplets size={18} /> },
  ];

  return (
    <div className="h-screen w-full bg-[#fef6d2] font-sans flex flex-col relative overflow-hidden">
      <Navbar />
      
      {/* Map Container */}
      <div className="flex-1 relative w-full h-full">
        <Map
          mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
          initialViewState={{
            longitude: 72.8777,
            latitude: 19.0760,
            zoom: 11
          }}
          mapStyle="mapbox://styles/mapbox/light-v11"
          onLoad={(e) => {
            const map = e.target;
            if (map.getLayer('background')) map.setPaintProperty('background', 'background-color', '#fef6d2');
            if (map.getLayer('water')) map.setPaintProperty('water', 'fill-color', '#fef6d2');
          }}
        >
          <NavigationControl position="bottom-right" />
        </Map>

        {/* Floating Data Options Layout */}
        <div className="absolute top-28 left-6 z-10 w-80 bg-[#8F9D68] backdrop-blur-xl text-black p-6 rounded-3xl shadow-[0_20px_50px_rgba(0,0,0,0.2)] border border-black/10">
          <div className="flex items-center gap-3 mb-6">
            <Layers className="text-black" size={24} />
            <h2 className="text-xl font-bold tracking-tight">Map Data</h2>
          </div>
          
          <div className="space-y-2">
            {layers.map((layer) => (
              <button 
                key={layer.id}
                onClick={() => setActiveLayer(layer.id)}
                className={`w-full flex items-center gap-4 p-4 rounded-2xl transition-all duration-300 font-medium text-sm border
                  ${activeLayer === layer.id 
                    ? 'bg-black text-[#fef6d2] shadow-lg scale-[1.02] border-black' 
                    : 'bg-[#fef6d2]/30 hover:bg-[#fef6d2]/50 text-black/80 hover:text-black border-black/5'
                  }`}
              >
                <div className={`${activeLayer === layer.id ? 'text-brand-yellow' : 'text-black/60'}`}>
                  {layer.icon}
                </div>
                <span>{layer.label}</span>
              </button>
            ))}
          </div>

          <div className="mt-8 pt-6 border-t border-black/10">
            <h4 className="text-[10px] font-bold uppercase tracking-widest text-black/50 mb-2">Notice</h4>
            <p className="text-xs text-black/80 leading-relaxed font-medium">
              Select a layer above to visualize statistical road data on the map.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Maps;
