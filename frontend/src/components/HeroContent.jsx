const HeroContent = () => {
  return (
    <div className="flex flex-col items-center justify-start pt-20 md:pt-28 h-full max-w-5xl mx-auto text-center px-4">
      <h2 className="text-brand-yellow font-heading font-bold uppercase tracking-[0.2em] text-sm md:text-base mb-4 drop-shadow-md">
        Navigate Smarter. Travel Better.
      </h2>
      
      <h1 className="font-brush text-5xl md:text-[5.5rem] text-white leading-[1.1] mb-6 drop-shadow-lg" style={{textShadow: '0 4px 20px rgba(0,0,0,0.3)'}}>
        Find Your Best Path<br/>
        <span className="uppercase">With Asphr</span>
      </h1>
    </div>
  );
};

export default HeroContent;
