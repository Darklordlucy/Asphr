import React, { useState, useRef } from 'react';
import Navbar from '../components/Navbar';
import { Terminal, MapPin, Cpu, ArrowRight, X, Copy, Check } from 'lucide-react';

const CodeBlock = ({ code, language }) => {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="relative mt-2 mb-6">
      <div className="absolute top-3 right-3 flex items-center gap-2 z-10">
        <span className="text-[10px] text-[#fef6d2]/40 uppercase font-mono">{language}</span>
        <button 
          onClick={handleCopy}
          className="p-1.5 bg-white/5 hover:bg-white/10 rounded border border-white/10 transition-colors text-white"
        >
          {copied ? <Check size={14} className="text-brand-yellow" /> : <Copy size={14} />}
        </button>
      </div>
      <pre className="bg-[#09151b] border border-white/5 p-5 rounded-2xl overflow-x-auto font-mono text-sm leading-relaxed text-left text-[#fef6d2]/90 max-h-[300px]">
        <code>{code}</code>
      </pre>
    </div>
  );
};

const Services = () => {
  const [showSetupModal, setShowSetupModal] = useState(false);
  const [projectNameInput, setProjectNameInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [modalError, setModalError] = useState('');
  const [projects, setProjects] = useState(() => {
    try {
      const saved = localStorage.getItem('asphr_developer_projects');
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });

  const [generatedKey, setGeneratedKey] = useState('');
  const [copied, setCopied] = useState(false);
  const [activeSection, setActiveSection] = useState('api');
  const docsRef = useRef(null);

  const handleOpenSetupModal = () => {
    setProjectNameInput('');
    setPasswordInput('');
    setModalError('');
    setGeneratedKey('');
    setShowSetupModal(true);
  };

  const handleGenerateKey = (e) => {
    if (e) e.preventDefault();
    const name = projectNameInput.trim();
    const password = passwordInput.trim();

    if (!name || !password) {
      setModalError('Please enter both Project Name and Password.');
      return;
    }

    if (projects[name]) {
      setModalError('Warning: The API already exists for this project');
      return;
    }

    const randomHex = Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join('');
    const key = `asphr_live_pk_${randomHex}`;

    const updatedProjects = { ...projects, [name]: { key, password } };
    setProjects(updatedProjects);
    try {
      localStorage.setItem('asphr_developer_projects', JSON.stringify(updatedProjects));
    } catch (err) {
      console.error('Failed to save to localStorage:', err);
    }

    setGeneratedKey(key);
    setCopied(false);
    setModalError('');
  };

  const handleCardClick = (sectionId) => {
    setActiveSection(sectionId);
    setTimeout(() => {
      docsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
  };

  const services = [
    {
      icon: <Terminal size={32} className="text-brand-yellow" />,
      title: "API Integration",
      description: "Connect your custom software seamlessly with our powerful API infrastructure. Access real-time routing, road safety scores, and incident reports programmatically.",
      link: "View Documentation",
      section: "api"
    },
    {
      icon: <MapPin size={32} className="text-brand-yellow" />,
      title: "Geocoding Services",
      description: "Fast and reliable geocoding engine. Convert raw geographic coordinates into human-readable addresses, or turn addresses into precise map points instantly.",
      link: "Explore Geocoding",
      section: "geocoding"
    },
    {
      icon: <Cpu size={32} className="text-brand-yellow" />,
      title: "MCP Server Support",
      description: "Built for the AI era. Natively supports the Model Context Protocol (MCP), allowing AI agents and LLMs to securely hook directly into our live data pipeline.",
      link: "Setup MCP",
      section: "mcp"
    }
  ];

  return (
    <div className="min-h-screen w-full bg-[#fef6d2] text-brand-dark font-sans overflow-x-hidden">
      <Navbar theme="light" />
      
      <div className="pt-32 px-6 md:px-10 lg:px-16 pb-20 w-full">
        <div className="mb-16">
          <h2 className="text-brand-dark/60 font-heading font-bold uppercase tracking-[0.2em] text-sm md:text-base mb-4">
            Developer Platform
          </h2>
          <h1 className="text-5xl md:text-7xl font-black font-sans text-brand-dark mb-6 tracking-tighter leading-none max-w-5xl">
            Powering the next generation of mobility.
          </h1>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-8 mt-6">
            <p className="text-brand-dark/70 text-xl max-w-4xl leading-relaxed">
              Integrate ASPHR's robust road intelligence and routing algorithms directly into your own applications, fleet management tools, and AI systems.
            </p>
            <button 
              onClick={handleOpenSetupModal}
              className="bg-[#0F2027] hover:bg-black text-brand-yellow px-5 py-2.5 rounded-full font-bold text-sm transition-all hover:scale-105 active:scale-95 shadow-md whitespace-nowrap self-start md:self-center shrink-0"
            >
              Generate API
            </button>
          </div>
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
              <button 
                onClick={() => handleCardClick(service.section)}
                className="flex items-center gap-2 text-black font-bold hover:text-black/70 transition-colors group/btn w-fit"
              >
                {service.link}
                <ArrowRight size={18} className="group-hover/btn:translate-x-1 transition-transform" />
              </button>
            </div>
          ))}
        </div>

        {/* Interactive Developer Guides */}
        <div ref={docsRef} className="mt-16 scroll-mt-28">
          {activeSection && (
            <div className="bg-[#8F9D68] text-black p-8 md:p-12 rounded-3xl shadow-2xl border border-black/10 animate-in fade-in slide-in-from-bottom-5 duration-300">
              {/* Tab navigation headers */}
              <div className="flex flex-wrap gap-4 border-b border-black/10 pb-6 mb-8">
                <button 
                  onClick={() => setActiveSection('api')}
                  className={`px-5 py-2.5 rounded-full font-bold text-sm transition-all ${activeSection === 'api' ? 'bg-black text-brand-yellow' : 'bg-black/10 hover:bg-black/20 text-black'}`}
                >
                  API Integration
                </button>
                <button 
                  onClick={() => setActiveSection('geocoding')}
                  className={`px-5 py-2.5 rounded-full font-bold text-sm transition-all ${activeSection === 'geocoding' ? 'bg-black text-brand-yellow' : 'bg-black/10 hover:bg-black/20 text-black'}`}
                >
                  Geocoding Engine
                </button>
                <button 
                  onClick={() => setActiveSection('mcp')}
                  className={`px-5 py-2.5 rounded-full font-bold text-sm transition-all ${activeSection === 'mcp' ? 'bg-black text-brand-yellow' : 'bg-black/10 hover:bg-black/20 text-black'}`}
                >
                  MCP Configuration
                </button>
              </div>

              {/* Content rendering based on activeSection */}
              {activeSection === 'api' && (
                <div className="animate-in fade-in duration-300 space-y-6">
                  <div>
                    <h3 className="text-3xl font-bold text-black mb-2 font-heading">API Integration Guide</h3>
                    <p className="text-black/75 text-lg">
                      Query the ASPHR platform directly from your application to fetch safe navigation paths, risk analytics, and real-time hazard locations.
                    </p>
                  </div>
                  
                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 mt-8">
                    <div>
                      <h4 className="text-lg font-bold text-black mb-2 font-heading">1. Request Syntax (cURL)</h4>
                      <p className="text-sm text-black/70 mb-3">
                        Use standard Authorization headers with your ASPHR developer token to request route safety.
                      </p>
                      <CodeBlock 
                        language="curl" 
                        code={`curl -X GET "https://api.asphr.io/v1/routes" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -d "origin=19.0760,72.8777" \\
  -d "destination=19.2183,72.9781" \\
  -d "avoid_hazards=true"`} 
                      />
                      
                      <h4 className="text-lg font-bold text-black mb-2 mt-6 font-heading">2. JavaScript Integration</h4>
                      <p className="text-sm text-black/70 mb-3">
                        Integrate standard routing directly into your React, Node, or mobile clients.
                      </p>
                      <CodeBlock 
                        language="javascript" 
                        code={`const fetchSafeRoute = async () => {
  const res = await fetch('https://api.asphr.io/v1/routes?origin=19.0760,72.8777&destination=19.2183,72.9781&avoid_hazards=true', {
    headers: {
      'Authorization': 'Bearer asphr_live_pk_sample_key'
    }
  });
  const data = await res.json();
  console.log('Safety score:', data.route.safety_score);
};`} 
                      />
                    </div>

                    <div>
                      <h4 className="text-lg font-bold text-black mb-2 font-heading">3. Sample API Response (JSON)</h4>
                      <p className="text-sm text-black/70 mb-3">
                        The routing engine returns safe segment matches, overall route safety index, and mapped alerts.
                      </p>
                      <CodeBlock 
                        language="json" 
                        code={`{
  "status": "success",
  "route": {
    "distance_km": 24.5,
    "duration_mins": 42,
    "safety_score": 94,
    "conditions": {
      "road_hazards_avoided": 4,
      "pothole_warnings": 1,
      "heavy_traffic_slowdown": false
    },
    "coordinates": [
      [72.8777, 19.0760],
      [72.9781, 19.2183]
    ]
  }
}`} 
                      />
                    </div>
                  </div>
                </div>
              )}

              {activeSection === 'geocoding' && (
                <div className="animate-in fade-in duration-300 space-y-6">
                  <div>
                    <h3 className="text-3xl font-bold text-black mb-2 font-heading">Geocoding Engine Architecture</h3>
                    <p className="text-black/75 text-lg">
                      ASPHR's geocoding subsystem handles high-throughput spatial indexing to translate coordinates to addresses, or resolve text queries to geographic markers.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 mt-8">
                    <div className="space-y-6">
                      <div>
                        <h4 className="text-lg font-bold text-black mb-2 font-heading">Reverse Geocoding Resolution</h4>
                        <p className="text-sm text-black/80 leading-relaxed">
                          When coordinates are submitted, our engine uses a custom **KD-Tree index structure** to perform a nearest-neighbor lookup within a 50-meter radius, matching coordinates directly against ASPHR's digitized MMR road network.
                        </p>
                      </div>

                      <div>
                        <h4 className="text-lg font-bold text-black mb-2 font-heading">Fuzzy Text Parsing</h4>
                        <p className="text-sm text-black/80 leading-relaxed">
                          For forward geocoding (text searches), the query is parsed using a tokenized text engine combined with regional address templates. It retrieves the highest confidence matches along with spatial boundary coordinates.
                        </p>
                      </div>

                      <div>
                        <h4 className="text-lg font-bold text-black mb-2 font-heading">Geocoding Endpoint (cURL)</h4>
                        <CodeBlock 
                          language="curl" 
                          code={`curl -X GET "https://api.asphr.io/v1/geocode/search?q=Thane+Station" \\
  -H "Authorization: Bearer YOUR_API_KEY"`} 
                        />
                      </div>
                    </div>

                    <div>
                      <h4 className="text-lg font-bold text-black mb-2 font-heading">Geocode Response Schema (JSON)</h4>
                      <p className="text-sm text-black/70 mb-3">
                        Returns localized street segments, confidence scores, and raw geographic output.
                      </p>
                      <CodeBlock 
                        language="json" 
                        code={`{
  "query": "Thane Station",
  "results": [
    {
      "formatted_address": "Thane East, Thane, Maharashtra 400603",
      "coordinates": [72.9781, 19.1860],
      "confidence": 0.98,
      "metadata": {
        "zone": "MMR East",
        "administrative_region": "Thane Municipal Corporation"
      }
    }
  ]
}`} 
                      />
                    </div>
                  </div>
                </div>
              )}

              {activeSection === 'mcp' && (
                <div className="animate-in fade-in duration-300 space-y-6">
                  <div>
                    <h3 className="text-3xl font-bold text-black mb-2 font-heading">MCP Integration Server</h3>
                    <p className="text-black/75 text-lg">
                      Natively bridge Large Language Models and AI agents directly with ASPHR's routing, hazards, and coordinates tools using the open Model Context Protocol.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 mt-8">
                    <div>
                      <h4 className="text-lg font-bold text-black mb-2 font-heading">1. Claude Desktop Server Configuration</h4>
                      <p className="text-sm text-black/70 mb-3">
                        Add ASPHR as a tool server by putting this block in your <code className="bg-black/10 px-2 py-1 rounded text-xs font-mono">claude_desktop_config.json</code>.
                      </p>
                      <CodeBlock 
                        language="json" 
                        code={`{
  "mcpServers": {
    "asphr-mobility-server": {
      "command": "npx",
      "args": ["-y", "@asphr/mcp-server"],
      "env": {
        "ASPHR_API_KEY": "YOUR_API_KEY"
      }
    }
  }
}`} 
                      />
                    </div>

                    <div>
                      <h4 className="text-lg font-bold text-black mb-2 font-heading">2. Python Agent Integration</h4>
                      <p className="text-sm text-black/70 mb-3">
                        Integrate the ASPHR MCP server into your custom AI pipelines using python.
                      </p>
                      <CodeBlock 
                        language="python" 
                        code={`import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="npx",
    args=["-y", "@asphr/mcp-server"],
    env={"ASPHR_API_KEY": "YOUR_API_KEY"}
)

async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Discover and query tools
            result = await session.call_tool("get_route_safety", {
                "origin": "19.0760,72.8777",
                "destination": "19.2183,72.9781"
            })
            print(result)

asyncio.run(main())`} 
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
        
        {/* API Key CTA */}
        <div className="mt-20 bg-[#8F9D68] text-black p-12 rounded-3xl relative overflow-hidden flex flex-col md:flex-row items-center justify-between shadow-2xl border border-black/10">
          
          <div className="relative z-10 max-w-xl mb-8 md:mb-0">
            <h2 className="text-3xl font-bold mb-4">Ready to start building?</h2>
            <p className="text-black/80 text-lg font-medium">
              Get your free developer API key today and start making requests to the ASPHR network within minutes.
            </p>
          </div>
          
          <button 
            onClick={handleOpenSetupModal}
            className="relative z-10 bg-black hover:bg-black/80 text-brand-yellow px-8 py-4 rounded-xl font-bold text-lg whitespace-nowrap transition-transform hover:scale-105 active:scale-95 shadow-xl"
          >
            Generate API Key
          </button>
        </div>
      </div>

      {/* API Generation Modal */}
      {showSetupModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#8F9D68] border border-black/20 rounded-3xl p-8 max-w-md w-full shadow-2xl relative animate-in fade-in zoom-in duration-200 text-black">
            <button 
              onClick={() => setShowSetupModal(false)}
              className="absolute top-4 right-4 text-black/60 hover:text-black transition-colors"
            >
              <X size={24} />
            </button>

            {!generatedKey ? (
              <form onSubmit={handleGenerateKey} className="space-y-5">
                <h3 className="text-2xl font-bold font-heading">Setup API Key</h3>
                <p className="text-black/80 text-sm font-medium">
                  Enter a project name and set a password to register your developer credentials and generate your secure API token.
                </p>

                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider mb-1.5 text-black/85">Project Name</label>
                    <input 
                      type="text" 
                      required
                      placeholder="e.g. Safe Route App"
                      value={projectNameInput}
                      onChange={(e) => {
                        setProjectNameInput(e.target.value);
                        if (modalError) setModalError('');
                      }}
                      className="w-full bg-[#fef6d2] border border-black/20 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-black font-semibold text-black placeholder-black/30"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider mb-1.5 text-black/85">Password</label>
                    <input 
                      type="password" 
                      required
                      placeholder="••••••••"
                      value={passwordInput}
                      onChange={(e) => {
                        setPasswordInput(e.target.value);
                        if (modalError) setModalError('');
                      }}
                      className="w-full bg-[#fef6d2] border border-black/20 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-black font-semibold text-black placeholder-black/30"
                    />
                  </div>
                </div>

                {modalError && (
                  <div className="p-3 bg-red-100 border border-red-300 text-red-800 text-xs font-bold rounded-xl flex items-center gap-2">
                    <span>{modalError}</span>
                  </div>
                )}

                <button 
                  type="submit"
                  disabled={!projectNameInput.trim() || !passwordInput.trim()}
                  className="w-full bg-black hover:bg-black/80 text-brand-yellow py-3 rounded-xl font-bold transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none shadow-lg"
                >
                  Generate Key
                </button>
              </form>
            ) : (
              <div className="space-y-5">
                <h3 className="text-2xl font-bold font-heading">Your ASPHR API Key</h3>
                <p className="text-black/80 text-sm font-medium">
                  Copy and save this key securely. You won't be able to retrieve it again.
                </p>
                <div className="flex items-center gap-2 bg-black/15 p-3 rounded-xl select-all font-mono text-xs text-black border border-black/10 break-all">
                  <span className="flex-1 select-all">{generatedKey}</span>
                  <button 
                    onClick={() => {
                      navigator.clipboard.writeText(generatedKey);
                      setCopied(true);
                      setTimeout(() => setCopied(false), 2000);
                    }}
                    className="p-2 hover:bg-black/10 rounded-lg transition-colors text-black shrink-0"
                    title="Copy to clipboard"
                  >
                    {copied ? <Check size={18} className="text-green-900" /> : <Copy size={18} />}
                  </button>
                </div>
                <button 
                  onClick={() => setShowSetupModal(false)}
                  className="w-full bg-black hover:bg-black/80 text-brand-yellow py-3 rounded-xl font-bold transition-all hover:scale-[1.02] active:scale-[0.98]"
                >
                  Done
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Services;
