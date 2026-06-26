import React, { useEffect, useRef, useState } from 'react';

const FadeIn = ({ children, delay = 0, className = '' }) => {
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.1, rootMargin: '50px' }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      style={{ transitionDelay: `${delay}ms` }}
      className={`transition-all duration-1000 ease-out transform will-change-transform ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
      } ${className}`}
    >
      {children}
    </div>
  );
};

const IntroAsphr = () => {
  return (
    <section className="w-full max-w-5xl mx-auto px-6 md:px-12 pt-8 md:pt-12 pb-24 md:pb-32 text-center text-brand-dark font-sans bg-transparent">
      <div className="flex flex-col items-center justify-center space-y-12">
        {/* First Line - Medium font */}
        <FadeIn delay={0}>
          <p className="text-xl md:text-2xl lg:text-3xl font-medium tracking-wide text-brand-dark/80 max-w-3xl mx-auto leading-relaxed">
            Roads won't become safer overnight.<br />
            But every journey can.
          </p>
        </FadeIn>

        {/* Second Line - Bigger font */}
        <FadeIn delay={200}>
          <h2 className="flex items-center justify-center gap-4 sm:gap-6 text-4xl sm:text-6xl md:text-7xl lg:text-8xl font-black tracking-tighter text-brand-dark uppercase whitespace-nowrap">
            <span>Introducing</span>
            <img 
              src="/image.png" 
              alt="ASPHR Logo" 
              className="h-14 sm:h-24 md:h-28 lg:h-36 object-contain inline-block" 
            />
          </h2>
        </FadeIn>

        {/* Third Line - Medium font */}
        <FadeIn delay={400}>
          <p className="text-lg md:text-xl lg:text-2xl font-medium text-brand-dark/70 max-w-4xl mx-auto leading-relaxed">
            The first AI-architected navigation system built with one priority: getting you home safely.
          </p>
        </FadeIn>
      </div>
    </section>
  );
};

export default IntroAsphr;
