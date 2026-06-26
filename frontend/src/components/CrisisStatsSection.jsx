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
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-12'
      } ${className}`}
    >
      {children}
    </div>
  );
};

const CrisisStatsSection = () => {
  const barData = [
    { state: 'UTTAR PRADESH', value: 24118, color: 'bg-blue-500' },
    { state: 'TAMIL NADU', value: 18449, color: 'bg-blue-500' },
    { state: 'MAHARASHTRA', value: 15715, color: 'bg-green-500' },
    { state: 'MADHYA PRADESH', value: 14791, color: 'bg-green-500' },
    { state: 'KARNATAKA', value: 12398, color: 'bg-green-500' },
    { state: 'RAJASTHAN', value: 11588, color: 'bg-blue-300' },
    { state: 'ANDHRA PRADESH', value: 8346, color: 'bg-blue-300' },
    { state: 'GUJARAT', value: 7717, color: 'bg-blue-300' },
  ];
  const maxBarValue = 24118;

  return (
    <section className="w-full max-w-7xl mx-auto px-6 md:px-12 py-24 text-brand-dark font-sans bg-transparent">
      
      {/* Header */}
      <FadeIn className="text-center mb-16">
        <h4 className="text-blue-500 font-bold tracking-widest uppercase text-sm mb-6">
          The Scale of the Crisis
        </h4>
        <h2 className="text-5xl md:text-7xl font-black leading-tight max-w-4xl mx-auto">
          1.77 Lakh Indian lives lost on roads.
          <span className="block text-lg md:text-3xl font-bold text-brand-dark/80 mt-4 tracking-normal">
            Every year. No warning. No system.
          </span>
        </h2>
      </FadeIn>

      {/* Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column (Cards) */}
        <div className="flex flex-col gap-6">
          <FadeIn delay={100} className="bg-[#8F9D68] text-black p-8 rounded-3xl shadow-xl border border-black/5">
            <div className="text-5xl font-bold mb-2">2,385</div>
            <div className="text-black/50 text-xs font-bold tracking-widest uppercase">Pothole Fatalities in 2024</div>
          </FadeIn>

          <FadeIn delay={200} className="bg-[#8F9D68] text-black p-8 rounded-3xl shadow-xl border border-black/5">
            <div className="text-5xl font-bold mb-2">+53%</div>
            <div className="text-black/50 text-xs font-bold tracking-widest uppercase">Rise Since 2020</div>
          </FadeIn>

          <FadeIn delay={300} className="bg-[#8F9D68] text-black p-8 rounded-3xl shadow-xl border border-black/5">
            <div className="text-5xl font-bold mb-2">54%</div>
            <div className="text-black/50 text-xs font-bold tracking-widest uppercase">Concentrated in Uttar Pradesh Alone</div>
          </FadeIn>

          <FadeIn delay={400} className="bg-[#8F9D68] text-black p-8 rounded-3xl shadow-xl border border-black/5">
            <div className="text-blue-400 text-xs font-bold tracking-widest uppercase mb-4">What This Means</div>
            <div className="text-2xl font-bold leading-snug mb-6">
              53,153 deaths due to delayed medical response.
            </div>
            <div className="text-black/40 text-[10px] tracking-widest uppercase">
              Sources: MoRTH - NITI Aayog - NCRB
            </div>
          </FadeIn>
        </div>

        {/* Right Column (Charts) */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          
          {/* Top Bar Chart */}
          <FadeIn delay={300} className="bg-[#8F9D68] text-black p-8 rounded-3xl shadow-xl border border-black/5 flex-1">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-6 h-px bg-blue-500"></div>
              <div className="text-black/40 text-[10px] tracking-widest uppercase">NITI Aayog - Ambulance Audit</div>
            </div>
            <h3 className="text-3xl font-bold mb-2">
              Road Fatalities by State — <span className="text-blue-500">2024</span>
            </h3>
            <p className="text-black/60 mb-8 text-sm">1,77,177 lives lost. Data from MoRTH Provisional 2024.</p>

            {/* Custom Bar Chart */}
            <div className="space-y-4 relative">
              {/* Vertical Grid Lines */}
              <div className="absolute inset-0 flex justify-between pointer-events-none px-32">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-full w-px bg-black/5"></div>
                ))}
              </div>

              {barData.map((item, index) => (
                <div key={index} className="flex items-center text-xs relative z-10">
                  <div className="w-32 text-right pr-4 text-black/50 font-medium tracking-wide text-[10px]">
                    {item.state}
                  </div>
                  <div className="flex-1 h-1.5 bg-black/5 rounded-full overflow-hidden relative group">
                    <div 
                      className={`h-full ${item.color} rounded-full transition-all duration-1000 ease-out`}
                      style={{ width: `${(item.value / maxBarValue) * 100}%` }}
                    ></div>
                  </div>
                  <div className="w-12 text-right pl-3 text-black/50 text-[10px]">
                    {item.value}
                  </div>
                </div>
              ))}
            </div>
          </FadeIn>

          {/* Bottom Pie Charts Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* Donut 1 */}
            <FadeIn delay={500} className="bg-[#8F9D68] text-black p-8 rounded-3xl shadow-xl border border-black/5">
              <div className="flex items-center gap-4 mb-4">
                <div className="w-6 h-px bg-blue-500"></div>
                <div className="text-black/40 text-[10px] tracking-widest uppercase">Rajya Sabha Q. 1871</div>
              </div>
              <h3 className="text-xl font-bold mb-1">
                Pothole Fatalities — <span className="text-blue-500">2020-2024</span>
              </h3>
              <p className="text-black/60 text-xs mb-8">9,438 lives lost. 54% concentrated in UP.</p>
              
              <div className="flex items-center gap-6">
                <div className="relative w-32 h-32 rounded-full flex items-center justify-center"
                     style={{ background: 'conic-gradient(#f97316 0% 54%, #a855f7 54% 64%, #3b82f6 64% 71%, #22c55e 71% 100%)' }}>
                  <div className="w-24 h-24 bg-[#8F9D68] rounded-full flex flex-col items-center justify-center shadow-inner">
                    <span className="font-bold text-xl">9438</span>
                    <span className="text-[8px] text-black/50 uppercase tracking-widest">Total 5-YR</span>
                  </div>
                </div>
                <div className="flex-1 space-y-3 text-[10px]">
                  <div className="flex justify-between items-center"><div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-orange-500"></div>Uttar Pradesh</div><span className="text-black/50">5127</span></div>
                  <div className="flex justify-between items-center"><div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-purple-500"></div>Madhya Pradesh</div><span className="text-black/50">969</span></div>
                  <div className="flex justify-between items-center"><div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-blue-500"></div>Tamil Nadu</div><span className="text-black/50">612</span></div>
                  <div className="flex justify-between items-center"><div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-green-500"></div>Odisha</div><span className="text-black/50">425</span></div>
                </div>
              </div>
            </FadeIn>

            {/* Donut 2 */}
            <FadeIn delay={600} className="bg-[#8F9D68] text-black p-8 rounded-3xl shadow-xl border border-black/5">
              <div className="flex items-center gap-4 mb-4">
                <div className="w-6 h-px bg-blue-500"></div>
                <div className="text-black/40 text-[10px] tracking-widest uppercase">MoRTH Annual Report</div>
              </div>
              <h3 className="text-xl font-bold mb-1">
                Fatalities by User — <span className="text-blue-500">2024</span>
              </h3>
              <p className="text-black/60 text-xs mb-8">2-wheelers represent the highest risk demographic.</p>
              
              <div className="flex items-center gap-6">
                <div className="relative w-32 h-32 rounded-full flex items-center justify-center"
                     style={{ background: 'conic-gradient(#ef4444 0% 44%, #a855f7 44% 63%, #3b82f6 63% 67%, #64748b 67% 100%)' }}>
                  <div className="w-24 h-24 bg-[#8F9D68] rounded-full flex flex-col items-center justify-center shadow-inner">
                    <span className="font-bold text-xl">1.77L</span>
                    <span className="text-[8px] text-black/50 uppercase tracking-widest">Total 2024</span>
                  </div>
                </div>
                <div className="flex-1 space-y-3 text-[10px]">
                  <div className="flex justify-between items-center"><div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-red-500"></div>2-Wheelers</div><span className="text-black/50">44%</span></div>
                  <div className="flex justify-between items-center"><div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-purple-500"></div>Pedestrians</div><span className="text-black/50">19%</span></div>
                  <div className="flex justify-between items-center"><div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-blue-500"></div>Cyclists</div><span className="text-black/50">4%</span></div>
                  <div className="flex justify-between items-center"><div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-slate-500"></div>Others</div><span className="text-black/50">33%</span></div>
                </div>
              </div>
            </FadeIn>

          </div>
        </div>
      </div>
    </section>
  );
};

export default CrisisStatsSection;
