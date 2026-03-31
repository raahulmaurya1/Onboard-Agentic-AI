import React from 'react';
import Navbar from '../components/Navbar';
import HeroSection from '../components/HeroSection';
import FeaturesSection from '../components/FeaturesSection';
import HowItWorks from '../components/HowItWorks';
import TrustSection from '../components/TrustSection';
import FAQSection from '../components/FAQSection';
import Footer from '../components/Footer';
import RobotWidget from '../components/RobotWidget';
export default function HomePage({ onGetStarted }) {
  return (
    <div>
      <Navbar onGetStarted={onGetStarted} />
      <HeroSection onGetStarted={onGetStarted} />
      <FeaturesSection />
      <HowItWorks />
      <TrustSection />
      <FAQSection />
      <Footer />
      <RobotWidget onGetStarted={onGetStarted} />
    </div>
  );
}
