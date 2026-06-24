const HeroContent = () => {
  return (
    <div className="flex flex-col items-center justify-center h-full max-w-5xl mx-auto text-center px-4 -mt-24 md:-mt-48">
      <h2 className="text-brand-yellow font-heading font-bold uppercase tracking-[0.2em] text-base md:text-xl mb-6 drop-shadow-md">
        Navigate Smarter. Travel Better.
      </h2>
      
      <h1 className="font-brush text-7xl md:text-[8.5rem] text-white leading-[1.05] mb-8 drop-shadow-lg" style={{textShadow: '0 4px 20px rgba(0,0,0,0.3)'}}>
        Find Your Best Path<br/>
        <span className="uppercase">With Asphr</span>
      </h1>
      
      {/* <p className="absolute bottom-8 md:bottom-12 left-1/2 -translate-x-1/2 w-full max-w-3xl px-4 text-white/90 font-sans text-lg md:text-2xl leading-relaxed drop-shadow text-center">
        Real-time traffic, safer routes, and smarter choices —<br/>
        all powered by data, designed for every journey.
      </p> */}
    </div>
  );
};

export default HeroContent;
