import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import Maps from './pages/Maps';
import RoutesPage from './pages/Routes';
import Services from './pages/Services';
import Dashboard from './pages/Dashboard';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/maps" element={<Maps />} />
      <Route path="/routes" element={<RoutesPage />} />
      <Route path="/services" element={<Services />} />
      <Route path="/dashboard" element={<Dashboard />} />
    </Routes>
  );
}

export default App;
