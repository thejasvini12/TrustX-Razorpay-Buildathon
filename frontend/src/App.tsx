import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { RiskFeedProvider } from './context/RiskFeedContext';
import { AppLayout } from './layouts/AppLayout';
import { OverviewPage } from './pages/OverviewPage';
import { RiskOperationsPage } from './pages/RiskOperationsPage';
import { AccountRiskPage } from './pages/AccountRiskPage';
import { FraudSpikePage } from './pages/FraudSpikePage';
import { FraudSpikeResultPage } from './pages/FraudSpikeResultPage';
import { AbuseRingPage } from './pages/AbuseRingPage';
import { AbuseRingResultPage } from './pages/AbuseRingResultPage';
import { SimulatorPage } from './pages/SimulatorPage';

export const App: React.FC = () => {
  return (
    <RiskFeedProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<OverviewPage />} />
            <Route path="/risk-operations" element={<RiskOperationsPage />} />
            <Route path="/account-risk" element={<AccountRiskPage />} />
            <Route path="/fraud-spike" element={<FraudSpikePage />} />
            <Route path="/fraud-spike/result" element={<FraudSpikeResultPage />} />
            <Route path="/abuse-ring" element={<AbuseRingPage />} />
            <Route path="/abuse-ring/result" element={<AbuseRingResultPage />} />
            <Route path="/simulator" element={<SimulatorPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </RiskFeedProvider>
  );
};

export default App;
