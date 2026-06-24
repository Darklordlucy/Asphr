import React from 'react';
import { Link } from 'react-router-dom';

const Logo = () => (
  <Link to="/" className="flex items-center">
    <img 
      src="/image.png" 
      alt="ASPHR Logo" 
      className="h-16 object-contain transition-all" 
    />
  </Link>
);

const ButtonLogo = () => (
  <svg width="14" height="14" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="mr-2 text-brand-yellow">
    <path d="M50 15 L15 85 L85 85 Z" fill="currentColor"/>
    <path d="M50 35 L30 75 L70 75 Z" fill="#0F2027"/>
  </svg>
);

const Navbar = ({ theme = 'dark' }) => {
  const isLight = theme === 'light';
  // Force black text and larger font size
  const linkClass = `transition-colors hover:text-brand-yellow text-brand-dark font-bold`;

  return (
    <nav className="flex items-center justify-between px-10 py-3 absolute top-0 w-full z-50">
      <Logo isLight={isLight} />
      
      <div className="hidden md:flex items-center space-x-10 text-lg">
        <Link to="/" className={linkClass}>Home</Link>
        <Link to="/maps" className={linkClass}>Maps</Link>
        <Link to="/routes" className={linkClass}>Routes</Link>
        <Link to="/services" className={linkClass}>Services</Link>
        <Link to="/dashboard" className={linkClass}>Dashboard</Link>
      </div>

      <button className="bg-[#0F2027] hover:bg-black text-white px-6 py-2.5 rounded-full font-sans font-medium text-sm flex items-center transition-all hover:scale-105 active:scale-95 shadow-xl border border-white/10">
        <ButtonLogo />
        Start Your Journey
      </button>
    </nav>
  );
};

export default Navbar;
