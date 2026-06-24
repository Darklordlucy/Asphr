import React from 'react';
import { ArrowRight } from 'lucide-react';

const Logo = () => (
  <div className="flex items-center">
    <svg width="32" height="32" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="mr-3">
      {/* A rough approximation of the ASPHR logo (overlapping angular shapes) */}
      <path d="M40 80 L50 20 L60 80" stroke="white" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M30 60 L70 60" stroke="white" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M15 95 L50 10 L85 95" stroke="white" strokeWidth="12" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
    <span className="font-heading font-bold text-2xl tracking-widest text-white">ASPHR</span>
  </div>
);

const Navbar = () => {
  return (
    <nav className="flex items-center justify-between px-10 py-6 absolute top-0 w-full z-50">
      <Logo />
      
      <div className="hidden md:flex items-center space-x-10 text-sm font-medium">
        <a href="#" className="hover:text-brand-yellow transition-colors text-white/90">Maps</a>
        <a href="#" className="hover:text-brand-yellow transition-colors text-white/90">Routes</a>
        <a href="#" className="hover:text-brand-yellow transition-colors text-white/90">Traffic</a>
        <a href="#" className="hover:text-brand-yellow transition-colors text-white/90">Explore</a>
        <a href="#" className="hover:text-brand-yellow transition-colors text-white/90">Asphr IoT</a>
      </div>

      <button className="bg-brand-yellow hover:bg-yellow-400 text-brand-dark px-6 py-2.5 rounded-full font-semibold text-sm flex items-center transition-transform hover:scale-105 active:scale-95 shadow-lg">
        Get Asphr
        <ArrowRight className="w-4 h-4 ml-2" />
      </button>
    </nav>
  );
};

export default Navbar;
