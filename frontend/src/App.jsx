import React from 'react';
import Navbar from './components/Navbar';
import HeroContent from './components/HeroContent';
import FeatureTimeline from './components/FeatureTimeline';
import { TriangleAlert } from 'lucide-react';

function App() {
  return (
    <div className="relative h-screen w-full bg-[url('/bg.jpeg')] bg-cover bg-center bg-no-repeat overflow-hidden font-sans">
      {/* Dark overlay gradient to ensure text readability */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/60 pointer-events-none"></div>

      <Navbar />
      <HeroContent />
      <FeatureTimeline />

      {/* Bottom left sign replica */}
      <div className="absolute bottom-10 left-10 hidden md:flex flex-col items-center">
        <div className="bg-black/40 backdrop-blur-md border border-white/20 p-4 rounded-lg flex flex-col items-center shadow-2xl">
          <TriangleAlert className="w-8 h-8 text-white/80 mb-2" />
          <div className="text-center font-heading font-semibold text-xs tracking-widest text-white/80">
            BETTER ROUTES<br/>
            BETTER JOURNEYS
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
