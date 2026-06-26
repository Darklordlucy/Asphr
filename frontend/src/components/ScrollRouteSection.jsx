import React, { useState, useEffect, useRef } from 'react';
import { Search, Shield, Info, MapPin, Eye, Play, Sparkles } from 'lucide-react';

const ScrollRouteSection = () => {
  const containerRef = useRef(null);
  const pathRef = useRef(null);
  const [progress, setProgress] = useState(0);
  const [markerPos, setMarkerPos] = useState({ x: 150, y: 50 });
  const [stops, setStops] = useState([]);

  const steps = [
    {
      title: "1. Search your destination",
      subtitle: "Set Origin & Destination",
      desc: "Search for locations on the map. The system reverse-geocodes addresses into geographical coordinates and snaps them to the nearest OSM road node.",
      icon: <Search className="w-6 h-6 text-blue-500" />,
      howToUse: "Go to the 'Routes' tab, and enter your origin and destination in the search inputs."
    },
    {
      title: "2. Tune your vehicle limits",
      subtitle: "Select Vehicle Profile",
      desc: "Specify your vehicle type (Bike, Car, Truck, Supercar). The engine dynamically adjusts filters, avoiding low clearance, narrow roads, or speed bumps if required.",
      icon: <Shield className="w-6 h-6 text-green-500" />,
      howToUse: "Select your vehicle type from the dynamic selector in the routing panel."
    },
    {
      title: "3. Choose routing objective",
      subtitle: "Tune Edge Weight Priorities",
      desc: "Choose from Safest (prioritizes low-vibration segments, avoids potholes & accidents), Fastest (live TomTom traffic and LSTM predictions), or Straightest routes.",
      icon: <Info className="w-6 h-6 text-purple-500" />,
      howToUse: "Toggle the routing modes on the main panel to instantly re-calculate routes."
    },
    {
      title: "4. Overlay active telemetry",
      subtitle: "Inspect Live IoT Heatmaps",
      desc: "Inspect live road friction, potholes, and accident hotspots generated directly from edge hardware accelerometers and gyroscopes on active vehicles.",
      icon: <Eye className="w-6 h-6 text-orange-500" />,
      howToUse: "Click on the Maps button to view real time sensor data."
    },
    {
      title: "5. Navigate and save lives",
      subtitle: "Start Safety Navigation",
      desc: "Follow turn-by-turn safe-path routing. The client dashboard logs your journey telemetry, contributing back to the safety network to keep others safe.",
      icon: <Play className="w-6 h-6 text-red-500" />,
      howToUse: "Click 'Start Your Journey' to open navigation "
    }
  ];

  useEffect(() => {
    let ticking = false;

    const handleScroll = () => {
      if (!containerRef.current) return;

      const rect = containerRef.current.getBoundingClientRect();
      const totalHeight = rect.height - window.innerHeight;
      if (totalHeight <= 0) return;

      const scrolled = -rect.top;
      const currentProgress = Math.max(0, Math.min(1, scrolled / totalHeight));
      setProgress(currentProgress);

      if (pathRef.current) {
        const totalLength = pathRef.current.getTotalLength();
        const currentLength = currentProgress * totalLength;
        const point = pathRef.current.getPointAtLength(currentLength);
        setMarkerPos({ x: point.x, y: point.y });
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('resize', handleScroll, { passive: true });

    // Initial run
    handleScroll();

    return () => {
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('resize', handleScroll);
    };
  }, []);

  // Compute stop positions on mount once path is rendered
  useEffect(() => {
    if (pathRef.current) {
      const totalLength = pathRef.current.getTotalLength();
      const computedStops = [0, 0.25, 0.5, 0.75, 1.0].map((p, idx) => {
        const point = pathRef.current.getPointAtLength(p * totalLength);
        return { x: point.x, y: point.y, label: String(idx + 1) };
      });
      setStops(computedStops);
    }
  }, []);

  const activeIdx = Math.min(4, Math.floor(progress * 5));

  return (
    <div 
      ref={containerRef} 
      className="relative bg-[#fef6d2] w-full"
      style={{ height: '400vh' }}
    >
      {/* Sticky viewport */}
      <div className="sticky top-0 h-screen w-full overflow-hidden flex flex-col lg:flex-row items-center justify-between px-6 md:px-16 py-10 gap-10">
        
        {/* Left Side: SVG Route Tracking */}
        <div className="flex-1 w-full flex items-center justify-center relative select-none">
          <div className="relative w-[340px] sm:w-[400px] aspect-[3/5] rounded-3xl overflow-hidden shadow-inner border border-brand-dark/5">
            {/* Background Map Image */}
            <img 
              src="/map_skeleton.png" 
              alt="Road Network Map" 
              className="absolute inset-0 w-full h-full object-cover opacity-65 mix-blend-multiply pointer-events-none"
            />
            
            {/* SVG Path */}
            <svg 
              viewBox="0 0 300 500" 
              className="w-full h-full overflow-visible relative z-10"
            >

              {/* Outer Road Base */}
              <path 
                ref={pathRef}
                d="M 130 20 L 130 65 Q 130 130, 240 130 L 240 165 Q 240 200, 170 200 L 170 245 Q 170 280, 60 280 L 60 315 Q 60 340, 150 340 L 210 340 Q 210 400, 170 400 L 170 450"
                fill="none" 
                stroke="#E9E2C8" 
                strokeWidth="24" 
                strokeLinecap="round"
              />
              {/* Road Center Dashes */}
              <path 
                d="M 130 20 L 130 65 Q 130 130, 240 130 L 240 165 Q 240 200, 170 200 L 170 245 Q 170 280, 60 280 L 60 315 Q 60 340, 150 340 L 210 340 Q 210 400, 170 400 L 170 450"
                fill="none" 
                stroke="#FFF" 
                strokeWidth="2" 
                strokeDasharray="8 12"
                strokeLinecap="round"
              />
              {/* Active Route Overlay */}
              <path 
                d="M 130 20 L 130 65 Q 130 130, 240 130 L 240 165 Q 240 200, 170 200 L 170 245 Q 170 280, 60 280 L 60 315 Q 60 340, 150 340 L 210 340 Q 210 400, 170 400 L 170 450"
                fill="none" 
                stroke="#3b82f6" 
                strokeWidth="8" 
                strokeLinecap="round"
                style={{
                  strokeDasharray: pathRef.current ? pathRef.current.getTotalLength() : 1000,
                  strokeDashoffset: pathRef.current ? pathRef.current.getTotalLength() * (1 - progress) : 1000
                }}
              />

              {/* Stop Indicators (Pins) */}
              {stops.map((stop, idx) => {
                const isPassed = progress >= idx * 0.25;
                return (
                  <g key={idx} transform={`translate(${stop.x}, ${stop.y})`}>
                    <circle 
                      r="16" 
                      className={`transition-colors duration-300 ${
                        isPassed ? 'fill-blue-500' : 'fill-white'
                      } stroke-brand-dark/10`} 
                      strokeWidth="2"
                    />
                    <text 
                      textAnchor="middle" 
                      dy="4" 
                      className={`text-xs font-black select-none pointer-events-none transition-colors duration-300 ${
                        isPassed ? 'fill-white' : 'fill-brand-dark/60'
                      }`}
                    >
                      {stop.label}
                    </text>
                  </g>
                );
              })}
            </svg>

            {/* Glowing Vehicle Marker */}
            {pathRef.current && (
              <div 
                className="absolute z-20 w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center shadow-[0_0_15px_rgba(59,130,246,0.6)] border-4 border-white pointer-events-none"
                style={{
                  left: `${(markerPos.x / 300) * 100}%`,
                  top: `${(markerPos.y / 500) * 100}%`,
                  transform: 'translate(-50%, -50%)',
                }}
              >
                <MapPin className="w-5 h-5 text-white" />
              </div>
            )}
          </div>
        </div>

        {/* Right Side: Step Content Cards */}
        <div className="flex-1 w-full max-w-3xl flex flex-col justify-center bg-[#8F9D68] text-black p-10 md:p-12 rounded-3xl shadow-xl border border-black/5 relative min-h-[580px] sm:min-h-[520px]">
          <div className="mb-3">
          </div>

          <h2 className="text-4xl md:text-5xl font-black text-black tracking-tight mb-8">
            How to Use Asphr
          </h2>

          <div className="relative min-h-[400px] sm:min-h-[350px]">
            {steps.map((step, idx) => {
              const isActive = idx === activeIdx;
              return (
                <div 
                  key={idx}
                  className={`absolute inset-0 flex flex-col justify-start transition-all duration-700 ease-out transform ${
                    isActive 
                      ? 'opacity-100 translate-y-0 pointer-events-auto' 
                      : 'opacity-0 translate-y-8 pointer-events-none'
                  }`}
                >
                  <div className="flex items-center gap-4 mb-4">
                    <div className="p-3.5 bg-white/80 rounded-2xl border border-black/5 shadow-md">
                      {step.icon}
                    </div>
                    <span className="text-xs md:text-sm font-bold uppercase tracking-wider text-black/60 font-heading">
                      {step.subtitle}
                    </span>
                  </div>

                  <h3 className="text-2xl md:text-3xl font-black text-black tracking-tight mb-3">
                    {step.title}
                  </h3>

                  <p className="text-black/75 text-base md:text-lg leading-relaxed mb-6 font-medium">
                    {step.desc}
                  </p>

                  <div className="bg-white/40 border border-white/20 p-6 rounded-2xl">
                    <div className="flex items-center gap-2 mb-2 text-xs md:text-sm font-extrabold uppercase tracking-wide text-black/75">
                      <Sparkles className="w-4 h-4 text-amber-500 fill-current" />
                      <span>Quick Guide</span>
                    </div>
                    <p className="text-black/90 text-sm md:text-base leading-relaxed font-semibold">
                      {step.howToUse}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Progress Indicators */}
          <div className="flex items-center gap-3 mt-8">
            {steps.map((_, idx) => (
              <div 
                key={idx}
                className={`h-2 rounded-full transition-all duration-500 ${
                  idx === activeIdx 
                    ? 'w-10 bg-black' 
                    : 'w-2 bg-black/20'
                }`}
              />
            ))}
          </div>
        </div>

      </div>
    </div>
  );
};

export default ScrollRouteSection;
