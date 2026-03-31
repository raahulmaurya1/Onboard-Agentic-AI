import React from 'react';
import styles from './TrustSection.module.css';

const TRUST_BADGES = [
  { icon: '🏦', label: 'RBI Regulated' },
  { icon: '🔒', label: '256-bit SSL' },
  { icon: '🛡️', label: 'DPDP Compliant' },
  { icon: '⚡', label: 'Instant KYC' },
];

const TESTIMONIALS = [
  {
    name: 'Priya Sharma',
    role: 'Small Business Owner, Delhi',
    text: 'Opened my current account in literally 90 seconds. The AI agent understood exactly what I needed. Absolutely blown away by the experience!',
    rating: 5,
    avatar: '👩‍💼',
  },
  {
    name: 'Rahul Verma',
    role: 'Software Engineer, Bangalore',
    text: 'Finally a bank that works for tech-savvy people. Zero paperwork, instant verification. The AI chat onboarding is genius.',
    rating: 5,
    avatar: '👨‍💻',
  },
  {
    name: 'Anjali Nair',
    role: 'Homemaker, Kochi',
    text: 'I was nervous about digital banking but Luna made it so easy. She guided me step by step. My account was ready before my chai got cold!',
    rating: 5,
    avatar: '👩',
  },
];

export default function TrustSection() {
  return (
    <section className={styles.section} id="trust">
      <div className={styles.container}>
        {/* Trust badges strip */}
        <div className={styles.badges}>
          {TRUST_BADGES.map((b) => (
            <div key={b.label} className={styles.badge}>
              <span className={styles.badgeIcon}>{b.icon}</span>
              <span className={styles.badgeLabel}>{b.label}</span>
            </div>
          ))}
        </div>

        {/* Header */}
        <div className={styles.header}>
          <span className={styles.sectionLabel}>Customer Stories</span>
          <h2 className={styles.title}>2 Million+ Happy Customers</h2>
        </div>

        {/* Testimonials */}
        <div className={styles.grid}>
          {TESTIMONIALS.map((t) => (
            <div key={t.name} className={styles.card}>
              <div className={styles.stars}>{'⭐'.repeat(t.rating)}</div>
              <p className={styles.text}>"{t.text}"</p>
              <div className={styles.author}>
                <div className={styles.avatar}>{t.avatar}</div>
                <div>
                  <div className={styles.name}>{t.name}</div>
                  <div className={styles.role}>{t.role}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
