import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import { Header } from '../components/Header';

const ROUTE_TITLES: Record<string, { title: string; subtitle: string }> = {
  '/': {
    title: 'Operations Center Overview',
    subtitle: 'High-Level Risk Telemetry, Attack Vectors & Model Health',
  },
  '/account-risk': {
    title: 'Account Risk & Return Abuse Hub',
    subtitle: 'Real-Time Coordinated Abuse Scoring & Serial Wardrobing Audit',
  },
  '/fraud-spike': {
    title: 'Temporal Fraud-Spike & 5-Min Telemetry',
    subtitle: 'Intra-Hour Velocity Bursts, P1 Guardrails & P3 Persistence Tracking',
  },
  '/fraud-spike/result': {
    title: 'Fraud Spike Assessment',
    subtitle: 'Operational assessment of merchant velocity and fraud-rate behavior',
  },
  '/abuse-ring': {
    title: 'Abuse-Ring Sentinel & Topology Explorer',
    subtitle: 'Bipartite Multi-Entity Graph Analysis & Account-Level Attribution',
  },
  '/simulator': {
    title: 'Attack Simulator & Analytics Studio',
    subtitle: 'Batch Stress-Testing & Defense Action Benchmarks',
  },
};

export const AppLayout: React.FC = () => {
  const location = useLocation();
  const currentRoute = ROUTE_TITLES[location.pathname] || {
    title: 'Operations Center',
    subtitle: 'TrustX Risk & Abuse Defense Platform',
  };

  return (
    <div className="app-container">
      <Sidebar />
      <div className="main-content">
        <Header title={currentRoute.title} subtitle={currentRoute.subtitle} />
        <main className="page-container">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
