import React, { useState } from 'react';
import styles from './FAQSection.module.css';

const FAQS = [
  {
    q: 'How long does it take to open an account?',
    a: 'With OnboardAI, you can open a fully functional bank account in under 2 minutes. Our AI agent guides you through the entire process — from collecting your details to verifying your identity — all through a simple chat interface.',
  },
  {
    q: 'What documents do I need to open an account?',
    a: 'You need a government-issued photo ID (Aadhaar, PAN, Passport, or Voter ID) and proof of address. Our AI can read and verify these documents instantly — just upload a photo.',
  },
  {
    q: 'Is my data safe and secure?',
    a: 'Absolutely. We use bank-grade 256-bit encryption for all data transmission and storage. Our platform is fully compliant with RBI guidelines and DPDP Act regulations. Your data is never shared with third parties.',
  },
  {
    q: 'What is Agentic AI and how does it help me?',
    a: 'Agentic AI is an advanced AI that can take actions on your behalf — not just answer questions. It fills forms, verifies documents, checks eligibility, and completes your onboarding automatically, just by having a conversation with you.',
  },
  {
    q: 'Can I access all banking services after onboarding?',
    a: 'Yes! Once onboarded, you get full access to savings accounts, fixed deposits, loans, insurance, and investment products. Your virtual debit card is issued instantly and your physical card is delivered within 3–5 business days.',
  },
  {
    q: 'What if I face an issue during onboarding?',
    a: 'Our AI agent Luna is available 24/7 to assist you. If she cannot resolve your issue, she escalates it to a human support executive immediately. You can also visit any of our branches.',
  },
  {
    q: 'Is there a minimum balance requirement?',
    a: 'Our zero-balance savings account has no minimum balance requirement. We believe banking should be accessible to everyone, regardless of their income or savings level.',
  },
];

export default function FAQSection() {
  const [openIdx, setOpenIdx] = useState(null);

  const toggle = (i) => setOpenIdx(openIdx === i ? null : i);

  return (
    <section className={styles.section} id="faq">
      <div className={styles.container}>
        {/* Header */}
        <div className={styles.header}>
          <span className={styles.sectionLabel}>FAQ</span>
          <h2 className={styles.title}>Frequently Asked Questions</h2>
          <p className={styles.subtitle}>
            Everything you need to know about OnboardAI and digital banking.
          </p>
        </div>

        {/* Accordion */}
        <div className={styles.list}>
          {FAQS.map((faq, i) => (
            <div
              key={i}
              className={`${styles.item} ${openIdx === i ? styles.itemOpen : ''}`}
            >
              <button className={styles.btn} onClick={() => toggle(i)}>
                <span className={styles.question}>{faq.q}</span>
                <span className={`${styles.icon} ${openIdx === i ? styles.iconOpen : ''}`}>
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path
                      d="M6 1V11M1 6H11"
                      stroke={openIdx === i ? '#1a1a2e' : '#888'}
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
                </span>
              </button>

              {openIdx === i && (
                <div className={styles.answer}>
                  <p>{faq.a}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
