import React, { useState, useEffect } from 'react';
import styles from './Navbar.module.css';

const NAV_LINKS = [
  { label: 'About Us', href: '#about-us' },
  { label: 'Services', href: '#services' },
  { label: 'Locate Us', href: '#locate-us' },
  { label: 'Helpdesk', href: '#helpdesk' },
];

export default function Navbar({ onGetStarted }) {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <nav className={`${styles.navbar} ${scrolled ? styles.scrolled : ''}`}>
      {/* Logo */}
      <div className={styles.logoWrap}>
        <img
          src={`${process.env.PUBLIC_URL}/logo.svg`}
          alt="OnboardAI"
          className={styles.logoImg}
        />
      </div>

      {/* Desktop links */}
      <div className={styles.desktopLinks}>
        {NAV_LINKS.map((link) => (
          <a key={link.label} href={link.href} className={styles.navLink}>
            {link.label}
          </a>
        ))}
        <button className={styles.btnPrimary} onClick={onGetStarted}>
          Get Started
        </button>
      </div>

      {/* Mobile hamburger */}
      <button
        className={styles.hamburger}
        onClick={() => setMobileOpen(!mobileOpen)}
        aria-label="Toggle menu"
      >
        <span className={`${styles.bar} ${mobileOpen ? styles.bar1Open : ''}`} />
        <span className={`${styles.bar} ${mobileOpen ? styles.bar2Open : ''}`} />
        <span className={`${styles.bar} ${mobileOpen ? styles.bar3Open : ''}`} />
      </button>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className={styles.mobileMenu}>
          {NAV_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className={styles.mobileLink}
              onClick={() => setMobileOpen(false)}
            >
              {link.label}
            </a>
          ))}
          <button
            className={styles.btnPrimary}
            onClick={() => { setMobileOpen(false); onGetStarted(); }}
            style={{ marginTop: '8px', width: '100%' }}
          >
            Get Started
          </button>
        </div>
      )}
    </nav>
  );
}
