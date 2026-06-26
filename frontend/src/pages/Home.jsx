import React from 'react';
import Navbar from '../components/Navbar';
import HeroContent from '../components/HeroContent';
import ChaptersSection from '../components/ChaptersSection';
import CrisisStatsSection from '../components/CrisisStatsSection';
import IntroAsphr from '../components/IntroAsphr';

const Home = () => {
  return (
    <div className="min-h-screen w-full bg-[#fef6d2] text-brand-dark font-sans">
      {/* Hero Section */}
      <div className="relative h-screen w-full bg-[url('/bg.jpeg')] bg-cover bg-center bg-no-repeat">

        <Navbar />
        <HeroContent />
      </div>

      {/* Chapters Stacking Section */}
      <ChaptersSection />

      {/* Crisis Stats Section */}
      <CrisisStatsSection />

      {/* Intro Asphr Section */}
      <IntroAsphr />
    </div>
  );
};

export default Home;
