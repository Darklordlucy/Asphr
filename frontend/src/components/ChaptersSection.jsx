import React, { useState, useEffect, useRef } from 'react';

const CHAPTER_IMAGES = [
  '/chapters/0.jpeg',
  '/chapters/1.png',
  '/chapters/2.PNG',
  '/chapters/3.PNG',
  '/chapters/4.PNG',
  '/chapters/5.PNG',
  '/chapters/6.PNG',
  '/chapters/7.PNG',
  '/chapters/8.PNG',
  '/chapters/9.PNG',
  '/chapters/10.PNG'
];

const ChaptersSection = () => {
  const containerRef = useRef(null);
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    let ticking = false;

    const updateScroll = () => {
      if (!containerRef.current) {
        ticking = false;
        return;
      }
      const rect = containerRef.current.getBoundingClientRect();
      const totalHeight = rect.height - window.innerHeight;
      if (totalHeight <= 0) {
        ticking = false;
        return;
      }
      
      const scrolled = -rect.top;
      const progress = Math.max(0, Math.min(1, scrolled / totalHeight));
      setScrollProgress(progress);
      ticking = false;
    };

    const handleScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(updateScroll);
        ticking = true;
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('resize', handleScroll, { passive: true });
    
    // Initial check
    updateScroll();

    return () => {
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('resize', handleScroll);
    };
  }, []);

  // Determine current active chapter index
  const activeIndex = Math.min(
    CHAPTER_IMAGES.length - 1,
    Math.floor(scrollProgress * CHAPTER_IMAGES.length)
  );

  return (
    <div 
      ref={containerRef} 
      className="relative bg-[#fef6d2] w-full"
      style={{ height: `${CHAPTER_IMAGES.length * 100 + 100}vh` }}
    >
      {/* Sticky viewport */}
      <div className="sticky top-0 h-screen w-full overflow-hidden flex flex-col md:flex-row items-center justify-between px-6 md:px-20 py-10">
        
        {/* Left Side: Dynamic Text / Indicators */}
        <div className="z-10 flex flex-col justify-center h-full w-full lg:w-1/4 text-left pointer-events-none mb-6 md:mb-0 shrink-0">
          <div className="text-brand-yellow font-heading font-bold uppercase tracking-[0.2em] text-base md:text-xl mb-4">
            Explore Chapters
          </div>
          <h2 className="text-6xl md:text-7xl lg:text-8xl font-black font-sans text-brand-dark mb-8 tracking-tighter leading-none">
            Journey Mode
          </h2>
          <p className="text-brand-dark/80 text-xl md:text-2xl leading-snug mb-12 font-medium">
            Scroll down to overlay the chapters and see how the journey unfolds step by step.
          </p>
          
          {/* Chapter step indicator */}
          <div className="flex items-end space-x-4">
            <span className="text-6xl md:text-7xl font-bold text-brand-yellow leading-none">
              {String(activeIndex + 1).padStart(2, '0')}
            </span>
            <div className="pb-2 text-xl md:text-2xl text-brand-dark/40 font-bold">
              / {String(CHAPTER_IMAGES.length).padStart(2, '0')}
            </div>
          </div>

          {/* Dots Indicator */}
          <div className="flex space-x-2 md:space-x-3 mt-8 flex-wrap gap-y-2">
            {CHAPTER_IMAGES.map((_, i) => (
              <div 
                key={i} 
                className={`h-2 md:h-3 rounded-full transition-all duration-300 ${
                  i === activeIndex 
                    ? 'w-10 md:w-16 bg-brand-yellow' 
                    : i < activeIndex 
                      ? 'w-3 md:w-4 bg-brand-yellow/50' 
                      : 'w-3 md:w-4 bg-brand-dark/20'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Right Side: Stacking Image Display */}
        <div className="relative w-full lg:w-3/4 h-[60vh] md:h-[85vh] flex items-center justify-center pl-0 lg:pl-12">
          {CHAPTER_IMAGES.map((src, index) => {
            // Calculate entry state
            const startProgress = index / CHAPTER_IMAGES.length;
            const endProgress = (index + 0.85) / CHAPTER_IMAGES.length;
            
            let localProgress = 0;
            if (scrollProgress >= startProgress) {
              localProgress = Math.min(1, (scrollProgress - startProgress) / (endProgress - startProgress));
            }

            const isVisible = scrollProgress >= startProgress;
            
            // Stack effects directly mapped to scroll progress for immediate feedback without CSS lag
            const translateY = isVisible ? (1 - localProgress) * 120 : 150;
            const scale = isVisible ? 0.9 + (localProgress * 0.1) : 0.85;
            
            // Fast fade in to prevent sudden appearance/disappearance, but fully opaque once stacked
            const opacity = isVisible ? Math.min(1, localProgress * 5) : 0;
            
            return (
              <div
                key={index}
                className="absolute"
                style={{
                  zIndex: index + 10,
                  opacity: opacity,
                  transform: `translate3d(0, ${translateY}px, 0) scale(${scale})`,
                  pointerEvents: index === activeIndex ? 'auto' : 'none',
                  maxWidth: '100%',
                  maxHeight: '100%',
                  willChange: 'transform, opacity'
                }}
              >
                <div className="bg-white p-1 md:p-1.5 rounded-xl border border-brand-dark/10 shadow-[0_20px_50px_rgba(0,0,0,0.3)]">
                  <img
                    src={src}
                    alt={`Chapter ${index}`}
                    className="rounded-lg object-contain max-h-[50vh] md:max-h-[75vh] w-auto"
                    loading="lazy"
                  />
                </div>
              </div>
            );
          })}
        </div>

      </div>
    </div>
  );
};

export default ChaptersSection;
