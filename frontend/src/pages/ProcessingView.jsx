import React from 'react';
import styles from './ChatbotOrchestrator.module.css';

export default function ProcessingView() {
  return (
    <div className={`${styles.viewCard} ${styles.processingView}`} role="status" aria-live="polite">
      <div className={styles.processingSpinner} aria-hidden="true" />
      <h2 className={styles.viewTitle}>Processing Documents</h2>
      <p className={styles.agentMessage}>Parsing and verifying your documents...</p>
      <p className={styles.metaText}>This can take a few moments.</p>
    </div>
  );
}
