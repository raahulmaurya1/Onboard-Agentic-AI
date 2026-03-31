import React from 'react';
import styles from './HowItWorks.module.css';

const STEPS = [
  {
    num: '01',
    title: 'Start a Conversation',
    desc: 'Click "Get Started" and our AI agent Luna greets you. Just tell her you want to open an account — no forms, no confusion.',
    variant: 'gold',
  },
  {
    num: '02',
    title: 'Provide Your Details',
    desc: 'Answer simple questions about yourself. Luna collects your name, contact info, and basic personal details through a natural chat flow.',
    variant: 'teal',
  },
  {
    num: '03',
    title: 'Upload Documents',
    desc: 'Share your ID proof and address verification. Our AI instantly reads and verifies your documents with zero manual effort.',
    variant: 'gold',
  },
  {
    num: '04',
    title: 'Complete KYC',
    desc: 'A quick selfie and biometric check confirms your identity. 100% secure, encrypted, and takes under 60 seconds.',
    variant: 'teal',
  },
  {
    num: '05',
    title: 'Account Activated',
    desc: "You're done! Your account is live, your virtual card is ready, and you can start banking immediately.",
    variant: 'gold',
    last: true,
  },
];

export default function HowItWorks() {
  return (
    <section className={styles.section} id="about-us">
      <div className={styles.decor} />

      <div className={styles.container}>
        {/* Header */}
        <div className={styles.header}>
          <span className={styles.label}>How It Works</span>
          <h2 className={styles.title}>Open Your Account in 5 Simple Steps</h2>
          <p className={styles.subtitle}>No paperwork. No branch visits. Just a conversation.</p>
        </div>

        {/* Steps */}
        <div className={styles.steps}>
          {STEPS.map((step) => (
            <div key={step.num} className={`${styles.step} ${step.last ? styles.stepLast : ''}`}>
              {/* Left: circle + connector */}
              <div className={styles.stepLeft}>
                <div className={`${styles.circle} ${styles[`circle_${step.variant}`]}`}>
                  {step.num}
                </div>
                {!step.last && <div className={styles.connector} />}
              </div>

              {/* Right: content */}
              <div className={styles.stepContent}>
                <h3 className={styles.stepTitle}>{step.title}</h3>
                <p className={styles.stepDesc}>{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
