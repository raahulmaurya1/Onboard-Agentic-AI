import React, { useState } from 'react';
import LoadingScreen from './components/LoadingScreen';
import HomePage from './pages/HomePage';
import OnboardingPage from './pages/OnboardingPage';

export default function App() {
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState('home'); // 'home' | 'onboarding'

  // Show onboarding chat page
  if (page === 'onboarding') {
    return <OnboardingPage onBack={() => setPage('home')} />;
  }

  return (
    <>
      {/* Loading screen overlays the home page while it mounts */}
      {loading && (
        <LoadingScreen onComplete={() => setLoading(false)} />
      )}

      {/* Home page renders behind loading screen so it's ready instantly */}
      <div
        style={{
          opacity: loading ? 0 : 1,
          transition: 'opacity 0.6s ease',
          pointerEvents: loading ? 'none' : 'all',
        }}
      >
        <HomePage onGetStarted={() => setPage('onboarding')} />
      </div>
    </>
  );
}
