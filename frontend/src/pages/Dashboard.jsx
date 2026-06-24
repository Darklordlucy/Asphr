import React, { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import { 
  User, MapPin, Briefcase, Car, LogOut, Settings, 
  Bell, Shield, Activity, Map, ChevronRight, Edit3
} from 'lucide-react';

// --- MOCK API DATA ---
// Easily replaceable with real API calls later
const MOCK_USER_PROFILE = {
  name: "John Doe",
  email: "john.doe@example.com",
  avatarUrl: "https://ui-avatars.com/api/?name=John+Doe&background=0F2027&color=fff",
  memberSince: "Jan 2024",
  status: "Premium",
  homeLocation: "Bandra West, Mumbai",
  workLocation: "Nariman Point, Mumbai",
  primaryVehicle: "SUV / Car",
  stats: {
    safetyRating: 94,
    totalRoutes: 128,
    reportsSubmitted: 15
  }
};

const MOCK_RECENT_ROUTES = [
  { id: 1, to: "Nariman Point", date: "Today, 08:30 AM", safetyScore: 95, distance: "14.2 km" },
  { id: 2, to: "Andheri East", date: "Yesterday, 18:15 PM", safetyScore: 88, distance: "8.5 km" },
  { id: 3, to: "Juhu Beach", date: "Oct 12, 09:00 AM", safetyScore: 92, distance: "5.1 km" }
];

const Dashboard = () => {
  // --- STATE ---
  // We initialize state with mock data. Later, start with null and use useEffect to fetch.
  const [user, setUser] = useState(MOCK_USER_PROFILE);
  const [routes, setRoutes] = useState(MOCK_RECENT_ROUTES);
  const [isLoggedIn, setIsLoggedIn] = useState(true);
  
  // Settings state
  const [notifications, setNotifications] = useState(true);
  const [privacyMode, setPrivacyMode] = useState(false);

  const handleLogout = () => {
    // Simulated logout
    setIsLoggedIn(false);
  };

  const handleLogin = () => {
    // Simulated login
    setIsLoggedIn(true);
  };

  if (!isLoggedIn) {
    return (
      <div className="min-h-screen w-full bg-[#fef6d2] font-sans flex flex-col items-center justify-center">
        <Navbar theme="light" />
        <div className="bg-[#8F9D68] p-12 rounded-3xl shadow-xl text-center max-w-md w-full mx-4 border border-black/10">
          <div className="w-20 h-20 bg-black rounded-full flex items-center justify-center mx-auto mb-6">
            <User size={40} className="text-[#8F9D68]" />
          </div>
          <h2 className="text-3xl font-bold text-black mb-4">Welcome Back</h2>
          <p className="text-black/80 font-medium mb-8">Please log in to view your personalized dashboard and routes.</p>
          <button 
            onClick={handleLogin}
            className="w-full bg-black text-[#fef6d2] hover:bg-black/80 font-bold py-4 rounded-xl transition-all shadow-lg hover:shadow-xl hover:-translate-y-1"
          >
            Log In
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full bg-[#fef6d2] font-sans overflow-x-hidden pb-20">
      <Navbar theme="light" />
      
      <div className="pt-32 px-6 md:px-10 max-w-7xl mx-auto">
        <div className="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <h1 className="text-4xl md:text-5xl font-black text-black tracking-tight mb-2">Your Dashboard</h1>
            <p className="text-black/60 font-medium text-lg">Manage your profile, preferences, and view your stats.</p>
          </div>
          <button 
            onClick={handleLogout}
            className="flex items-center gap-2 px-6 py-3 bg-black hover:bg-black/80 text-[#fef6d2] font-bold rounded-xl transition-colors shadow-lg"
          >
            <LogOut size={18} />
            Log Out
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* LEFT COLUMN: Profile & Settings */}
          <div className="lg:col-span-1 space-y-8">
            
            {/* Profile Card */}
            <div className="bg-[#8F9D68] p-8 rounded-3xl shadow-xl border border-black/10">
              <div className="flex items-center gap-4 mb-6">
                <img src={user.avatarUrl} alt="Avatar" className="w-20 h-20 rounded-full border-4 border-black/20" />
                <div>
                  <h2 className="text-2xl font-bold text-black leading-tight">{user.name}</h2>
                  <p className="text-black/70 font-medium">{user.email}</p>
                  <div className="inline-block mt-2 px-3 py-1 bg-black text-[#fef6d2] text-xs font-bold rounded-full uppercase tracking-wider">
                    {user.status}
                  </div>
                </div>
              </div>
              <div className="pt-6 border-t border-black/10">
                <p className="text-sm font-medium text-black/60 uppercase tracking-widest mb-1">Member Since</p>
                <p className="font-bold text-black">{user.memberSince}</p>
              </div>
            </div>

            {/* Settings Card */}
            <div className="bg-[#8F9D68] p-8 rounded-3xl shadow-xl border border-black/10">
              <div className="flex items-center gap-3 mb-6">
                <Settings className="text-black" size={24} />
                <h3 className="text-xl font-bold text-black">Settings</h3>
              </div>
              
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Bell size={18} className="text-black/60" />
                    <div>
                      <p className="font-bold text-black">Notifications</p>
                      <p className="text-xs text-black/60 font-medium">Route alerts & updates</p>
                    </div>
                  </div>
                  <button 
                    onClick={() => setNotifications(!notifications)}
                    className={`w-12 h-6 rounded-full transition-colors relative ${notifications ? 'bg-black' : 'bg-black/20'}`}
                  >
                    <div className={`absolute top-1 w-4 h-4 rounded-full bg-[#fef6d2] transition-transform ${notifications ? 'translate-x-7' : 'translate-x-1'}`} />
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Shield size={18} className="text-black/60" />
                    <div>
                      <p className="font-bold text-black">Privacy Mode</p>
                      <p className="text-xs text-black/60 font-medium">Anonymous location</p>
                    </div>
                  </div>
                  <button 
                    onClick={() => setPrivacyMode(!privacyMode)}
                    className={`w-12 h-6 rounded-full transition-colors relative ${privacyMode ? 'bg-black' : 'bg-black/20'}`}
                  >
                    <div className={`absolute top-1 w-4 h-4 rounded-full bg-[#fef6d2] transition-transform ${privacyMode ? 'translate-x-7' : 'translate-x-1'}`} />
                  </button>
                </div>
              </div>
            </div>

          </div>

          {/* RIGHT COLUMN: Preferences & History */}
          <div className="lg:col-span-2 space-y-8">
            
            {/* Stats Overview */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-[#8F9D68] p-6 rounded-3xl shadow-xl border border-black/10 flex flex-col items-center justify-center text-center">
                <Shield size={28} className="text-black mb-3" />
                <h4 className="text-4xl font-black text-black">{user.stats.safetyRating}</h4>
                <p className="text-xs font-bold text-black/60 uppercase tracking-widest mt-1">Safety Rating</p>
              </div>
              <div className="bg-[#8F9D68] p-6 rounded-3xl shadow-xl border border-black/10 flex flex-col items-center justify-center text-center">
                <Map size={28} className="text-black mb-3" />
                <h4 className="text-4xl font-black text-black">{user.stats.totalRoutes}</h4>
                <p className="text-xs font-bold text-black/60 uppercase tracking-widest mt-1">Total Routes</p>
              </div>
              <div className="bg-[#8F9D68] p-6 rounded-3xl shadow-xl border border-black/10 flex flex-col items-center justify-center text-center">
                <Activity size={28} className="text-black mb-3" />
                <h4 className="text-4xl font-black text-black">{user.stats.reportsSubmitted}</h4>
                <p className="text-xs font-bold text-black/60 uppercase tracking-widest mt-1">Reports</p>
              </div>
            </div>

            {/* Mobility Preferences */}
            <div className="bg-[#8F9D68] p-8 rounded-3xl shadow-xl border border-black/10">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold text-black">Mobility Preferences</h3>
                <button className="p-2 hover:bg-black/10 rounded-full transition-colors text-black">
                  <Edit3 size={18} />
                </button>
              </div>

              <div className="space-y-4">
                <div className="flex items-center gap-4 bg-[#fef6d2]/30 p-4 rounded-2xl border border-black/5">
                  <div className="w-10 h-10 bg-black rounded-xl flex items-center justify-center shrink-0">
                    <MapPin className="text-[#fef6d2]" size={18} />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-black/60 uppercase tracking-widest">Home Location</p>
                    <p className="font-bold text-black">{user.homeLocation}</p>
                  </div>
                </div>
                
                <div className="flex items-center gap-4 bg-[#fef6d2]/30 p-4 rounded-2xl border border-black/5">
                  <div className="w-10 h-10 bg-black rounded-xl flex items-center justify-center shrink-0">
                    <Briefcase className="text-[#fef6d2]" size={18} />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-black/60 uppercase tracking-widest">Work Location</p>
                    <p className="font-bold text-black">{user.workLocation}</p>
                  </div>
                </div>

                <div className="flex items-center gap-4 bg-[#fef6d2]/30 p-4 rounded-2xl border border-black/5">
                  <div className="w-10 h-10 bg-black rounded-xl flex items-center justify-center shrink-0">
                    <Car className="text-[#fef6d2]" size={18} />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-black/60 uppercase tracking-widest">Primary Vehicle</p>
                    <p className="font-bold text-black">{user.primaryVehicle}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Routes */}
            <div className="bg-[#8F9D68] p-8 rounded-3xl shadow-xl border border-black/10">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold text-black">Recent Routes</h3>
                <button className="text-sm font-bold text-black hover:text-black/60 transition-colors">View All</button>
              </div>
              
              <div className="space-y-3">
                {routes.map(route => (
                  <div key={route.id} className="group flex items-center justify-between p-4 bg-[#fef6d2]/30 hover:bg-[#fef6d2]/50 rounded-2xl transition-colors border border-black/5 cursor-pointer">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-black/10 rounded-full flex items-center justify-center">
                        <MapPin className="text-black" size={16} />
                      </div>
                      <div>
                        <p className="font-bold text-black">{route.to}</p>
                        <p className="text-xs font-medium text-black/60">{route.date} • {route.distance}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className="font-black text-black">{route.safetyScore}</p>
                        <p className="text-[10px] font-bold text-black/40 uppercase tracking-widest">Score</p>
                      </div>
                      <ChevronRight size={20} className="text-black/30 group-hover:text-black transition-colors" />
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
