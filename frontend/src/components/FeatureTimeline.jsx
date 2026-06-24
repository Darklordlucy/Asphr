import React from 'react';
import { ShieldCheck, Zap, Route, Users } from 'lucide-react';

const features = [
  { id: 1, title: 'SAFER\nROUTES', icon: <ShieldCheck className="w-6 h-6 text-white" />, bgColor: 'bg-brand-green' },
  { id: 2, title: 'FASTER\nTRAVEL', icon: <Zap className="w-6 h-6 text-white" />, bgColor: 'bg-brand-orange' },
  { id: 3, title: 'SMARTER\nCHOICES', icon: <Route className="w-6 h-6 text-white" />, bgColor: 'bg-brand-blue' },
  { id: 4, title: 'BUILT FOR\nEVERYONE', icon: <Users className="w-6 h-6 text-white" />, bgColor: 'bg-brand-purple' },
];

const FeatureTimeline = () => {
  return (
    <div className="absolute right-10 top-1/2 -translate-y-1/2 hidden lg:flex flex-col items-center">
      {features.map((feature, index) => (
        <div key={feature.id} className="relative flex flex-col items-center">
          {/* Timeline Node */}
          <div className="flex items-center group cursor-pointer relative z-10">
            {/* The Icon Circle */}
            <div className={`w-14 h-14 rounded-full flex items-center justify-center shadow-lg transition-transform hover:scale-110 ${feature.bgColor}`}>
              {feature.icon}
            </div>
            {/* Label (floating to the right) */}
            <div className="absolute left-[120%] whitespace-pre-line font-heading font-bold text-sm tracking-wide text-white drop-shadow-md group-hover:translate-x-1 transition-transform">
              {feature.title}
            </div>
          </div>
          
          {/* Dashed Line connecting to next item */}
          {index < features.length - 1 && (
            <div className="w-[2px] h-16 border-l-2 border-dashed border-white/50 my-1 z-0"></div>
          )}
        </div>
      ))}
    </div>
  );
};

export default FeatureTimeline;
