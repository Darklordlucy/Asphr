import React from 'react';
import Navbar from '../components/Navbar';

const Dashboard = () => {
  return (
    <div className="min-h-screen w-full bg-brand-oldlace text-brand-dark font-sans">
      <Navbar theme="light" />
      <div className="pt-32 px-10">
        <h1 className="text-4xl font-bold font-sans">Dashboard</h1>
        <p className="mt-4 text-brand-dark/60">This page is currently empty. Design coming soon.</p>
      </div>
    </div>
  );
};

export default Dashboard;
