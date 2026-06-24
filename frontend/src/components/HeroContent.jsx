import React from 'react';

const ButtonLogo = () => (
  <svg width="18" height="18" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="mr-3 text-brand-yellow">
    <path d="M50 15 L15 85 L85 85 Z" fill="currentColor"/>
    <path d="M50 35 L30 75 L70 75 Z" fill="#0F2027"/>
  </svg>
);

const HeroContent = () => {
  return (
    <div className="flex flex-col items-center justify-center h-full max-w-4xl mx-auto text-center px-4 pt-32">
      <h2 className="text-brand-yellow font-heading font-bold uppercase tracking-[0.2em] text-sm md:text-base mb-6 drop-shadow-md">
        Navigate Smarter. Travel Better.
      </h2>
      
      <h1 className="font-brush text-6xl md:text-8xl text-white leading-[1.1] mb-8 drop-shadow-lg" style={{textShadow: '0 4px 20px rgba(0,0,0,0.3)'}}>
        Find Your Best Path<br/>
        <span className="uppercase">With Asphr</span>
      </h1>
      
      <p className="text-white/90 font-sans text-base md:text-lg max-w-2xl leading-relaxed mb-10 drop-shadow">
        Real-time traffic, safer routes, and smarter choices —<br/>
        all powered by data, designed for every journey.
      </p>

      <button className="bg-[#0F2027] hover:bg-black text-white px-8 py-4 rounded-full font-sans font-medium text-lg flex items-center transition-all hover:scale-105 active:scale-95 shadow-xl border border-white/10">
        <ButtonLogo />
        Start Your Journey
      </button>
    </div>
  );
};

export default HeroContent;
