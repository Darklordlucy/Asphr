import React from 'react';
import Navbar from './components/Navbar';
import HeroContent from './components/HeroContent';

function App() {
  return (
    <div className="relative h-screen w-full bg-[url('/bg.jpeg')] bg-cover bg-center bg-no-repeat overflow-hidden font-sans">
      {/* Dark overlay gradient to ensure text readability */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/60 pointer-events-none"></div>

      <Navbar />
      <HeroContent />
    </div>
  );
}

export default App;
