import React from 'react';
import styles from './Footer.module.css';

const COLS = [
  {
    title: 'Quick Links',
    links: [
      { label: 'About Us', href: '#about-us' },
      { label: 'Services', href: '#services' },
      { label: 'Locate Us', href: '#locate-us' },
      { label: 'Helpdesk', href: '#helpdesk' },
      { label: 'Careers', href: '#' },
    ],
  },
  {
    title: 'Products',
    links: [
      { label: 'Savings Account', href: '#' },
      { label: 'Fixed Deposit', href: '#' },
      { label: 'Personal Loan', href: '#' },
      { label: 'Insurance', href: '#' },
      { label: 'Investments', href: '#' },
    ],
  },
  {
    title: 'Support',
    links: [
      { label: 'Contact Us', href: '#' },
      { label: 'Live Chat', href: '#' },
      { label: 'FAQs', href: '#faq' },
      { label: 'Security', href: '#' },
      { label: 'Privacy Policy', href: '#' },
    ],
  },
];

export default function Footer() {
  return (
    <footer className={styles.footer} id="helpdesk">
      <div className={styles.container}>
        {/* Top grid */}
        <div className={styles.grid}>
          {/* Brand column */}
          <div className={styles.brand}>
            <div className={styles.logoWrap}>
              <img
                src={`${process.env.PUBLIC_URL}/logo.svg`}
                alt="OnboardAI"
                // style={{ width: '330%' }}
              />
            </div>
            <p className={styles.brandDesc}>
              Transforming banking with agentic AI. Open accounts, manage finances,
              and get support — all through intelligent conversations.
            </p>
            <div className={styles.socials}>
              {['𝕏', 'in', 'f'].map((icon) => (
                <a key={icon} href="#" className={styles.socialBtn}>
                  {icon}
                </a>
              ))}
            </div>
          </div>

          {/* Link columns */}
          {COLS.map((col) => (
            <div key={col.title} className={styles.col}>
              <h4 className={styles.colTitle}>{col.title}</h4>
              <ul className={styles.colLinks}>
                {col.links.map((link) => (
                  <li key={link.label}>
                    <a href={link.href} className={styles.colLink}>
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className={styles.bottom}>
          <p className={styles.copy}>
            © 2024 OnboardAI. All rights reserved. | Regulated by Reserve Bank of India
          </p>
          <div className={styles.legal}>
            {['Terms of Service', 'Privacy Policy', 'Cookie Policy'].map((l) => (
              <a key={l} href="#" className={styles.legalLink}>
                {l}
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
