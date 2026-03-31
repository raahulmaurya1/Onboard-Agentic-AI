import React from 'react';
import Globe3D from './Globe3D';
import styles from './HeroSection.module.css';

export default function HeroSection({ onGetStarted }) {
  return (
    <section className={styles.hero} id="hero">
      {/* Decorative background blobs */}
      <div className={styles.blob1} />
      <div className={styles.blob2} />

      <div className={styles.grid}>
        {/* ── LEFT COLUMN ── */}
        <div className={styles.left}>
         
          {/* Heading */}
          <h1 className={styles.heading}>
            <span className={styles.headingLine}>BANKING  AT</span>
            <span className={styles.headingGold}>YOUR  FINGERTIPS</span>
          </h1>

          {/* Sub-heading */}
          <p className={styles.subHeading}>
            Experience seamless account opening and onboarding
            <br />
            with Agentic AI
          </p>

          {/* CTA buttons */}
          <div className={styles.ctas}>
            <button className={styles.btnPrimary} onClick={onGetStarted}>
              Get Started
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path
                  d="M3 8H13M13 8L9 4M13 8L9 12"
                  stroke="#1a1a2e"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            </button>
            <button className={styles.btnOutline} onClick={() => document.getElementById('about-us').scrollIntoView({ behavior: 'smooth' })}>How it works ?</button>
          </div>

          {/* Stats */}
          <div className={styles.stats}>
            {[
              { num: '2M+', label: 'Customers Onboarded' },
              { num: '99.9%', label: 'Uptime Guarantee' },
              { num: '<2 min', label: 'Account Opening' },
            ].map((s) => (
              <div key={s.label} className={styles.statItem}>
                <div className={styles.statNum}>{s.num}</div>
                <div className={styles.statLabel}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* ── RIGHT COLUMN – 3D Globe ── */}
        <div className={styles.right}>
          <div className={styles.globeGlow} />
          <Globe3D />
        </div>
      </div>
    </section>
  );
}
