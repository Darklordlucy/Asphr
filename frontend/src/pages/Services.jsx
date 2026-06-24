import React from 'react';
import Navbar from '../components/Navbar';
import { Terminal, MapPin, Cpu, ArrowRight } from 'lucide-react';

const Services = () => {
  const services = [
    {
      icon: <Terminal size={32} className="text-brand-yellow" />,
      title: "API Integration",
      description: "Connect your custom software seamlessly with our powerful API infrastructure. Access real-time routing, road safety scores, and incident reports programmatically.",
      link: "View Documentation"
    },
    {
      icon: <MapPin size={32} className="text-brand-yellow" />,
      title: "Geocoding Services",
      description: "Fast and reliable geocoding engine. Convert raw geographic coordinates into human-readable addresses, or turn addresses into precise map points instantly.",
      link: "Explore Geocoding"
    },
    {
      icon: <Cpu size={32} className="text-brand-yellow" />,
      title: "MCP Server Support",
      description: "Built for the AI era. Natively supports the Model Context Protocol (MCP), allowing AI agents and LLMs to securely hook directly into our live data pipeline.",
      link: "Setup MCP"
    }
  ];

  return (
    <div className="min-h-screen w-full bg-[#fef6d2] text-brand-dark font-sans overflow-x-hidden">
      <Navbar theme="light" />
      
      <div className="pt-32 px-6 md:px-20 pb-20 max-w-7xl mx-auto">
        <div className="mb-16">
          <h2 className="text-brand-yellow font-heading font-bold uppercase tracking-[0.2em] text-sm md:text-base mb-4">
            Developer Platform
          </h2>
          <h1 className="text-5xl md:text-7xl font-black font-sans text-brand-dark mb-6 tracking-tighter leading-none max-w-2xl">
            Powering the next generation of mobility.
          </h1>
          <p className="text-brand-dark/70 text-xl max-w-2xl leading-relaxed">
            Integrate ASPHR's robust road intelligence and routing algorithms directly into your own applications, fleet management tools, and AI systems.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {services.map((service, idx) => (
            <div 
              key={idx} 
              className="bg-[#8F9D68] p-8 rounded-3xl shadow-xl border border-black/10 hover:-translate-y-2 hover:shadow-2xl transition-all duration-300 group flex flex-col"
            >
              <div className="w-16 h-16 bg-black rounded-2xl flex items-center justify-center mb-8 group-hover:scale-110 transition-transform duration-300 shrink-0">
                {service.icon}
              </div>
              <h3 className="text-2xl font-bold mb-4 text-black">{service.title}</h3>
              <p className="text-black/80 leading-relaxed mb-8 flex-1 font-medium">
                {service.description}
              </p>
              <button className="flex items-center gap-2 text-black font-bold hover:text-black/70 transition-colors group/btn w-fit">
                {service.link}
                <ArrowRight size={18} className="group-hover/btn:translate-x-1 transition-transform" />
              </button>
            </div>
          ))}
        </div>
        
        {/* API Key CTA */}
        <div className="mt-20 bg-[#8F9D68] text-black p-12 rounded-3xl relative overflow-hidden flex flex-col md:flex-row items-center justify-between shadow-2xl border border-black/10">
          {/* Decorative background circle */}
          <div className="absolute top-[-50%] right-[-10%] w-96 h-96 bg-brand-yellow/30 rounded-full blur-3xl pointer-events-none"></div>
          
          <div className="relative z-10 max-w-xl mb-8 md:mb-0">
            <h2 className="text-3xl font-bold mb-4">Ready to start building?</h2>
            <p className="text-black/80 text-lg font-medium">
              Get your free developer API key today and start making requests to the ASPHR network within minutes.
            </p>
          </div>
          
          <button className="relative z-10 bg-black hover:bg-black/80 text-brand-yellow px-8 py-4 rounded-xl font-bold text-lg whitespace-nowrap transition-transform hover:scale-105 active:scale-95 shadow-xl">
            Generate API Key
          </button>
        </div>
      </div>
    </div>
  );
};

export default Services;
