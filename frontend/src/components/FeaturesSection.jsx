import React from 'react';
import styles from './FeaturesSection.module.css';

const FEATURES = [
  {
    icon: '🤖',
    title: 'Agentic AI Onboarding',
    desc: 'Our intelligent AI agent guides you through every step — collecting documents, verifying identity, and completing KYC in minutes.',
    accent: 'gold',
  },
  {
    icon: '🔐',
    title: 'Instant KYC Verification',
    desc: 'Advanced biometric checks and document verification powered by AI. No paperwork, no branch visits — seamless digital identity.',
    accent: 'teal',
  },
  {
    icon: '💳',
    title: 'Instant Account Issuance',
    desc: 'Receive your virtual debit card and account details immediately upon approval. Start transacting within minutes.',
    accent: 'gold',
  },
  // {
  //   icon: '📱',
  //   title: 'Mobile-First Experience',
  //   desc: 'Designed for smartphones first. Open your account, manage finances, and get support through our intuitive mobile interface.',
  //   accent: 'teal',
  // },
  // {
  //   icon: '🏦',
  //   title: 'Full Banking Services',
  //   desc: 'From savings accounts to loans, insurance to investments — access a complete suite of banking products in one platform.',
  //   accent: 'gold',
  // },
  // {
  //   icon: '🌐',
  //   title: 'Locate Any Branch',
  //   desc: 'Find the nearest branch or ATM with real-time availability. Schedule appointments or resolve issues remotely.',
  //   accent: 'teal',
  // },
];

export default function FeaturesSection() {
  return (
    <section className={styles.section} id="services">
      <div className={styles.container}>
        {/* Header */}
        <div className={styles.header}>
          <span className={styles.sectionLabel}>Our Services</span>
          <h2 className={styles.title}>Everything You Need to Bank Smarter</h2>
          <p className={styles.subtitle}>
            Powered by cutting-edge AI and designed for the digital generation of banking customers.
          </p>
        </div>

        {/* Grid */}
        <div className={styles.grid}>
          {FEATURES.map((f) => (
            <div key={f.title} className={`${styles.card} ${styles[`accent_${f.accent}`]}`}>
              <div className={styles.cardIcon}>{f.icon}</div>
              <h3 className={styles.cardTitle}>{f.title}</h3>
              <p className={styles.cardDesc}>{f.desc}</p>
              <div className={`${styles.cardDot} ${styles[`dot_${f.accent}`]}`} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
