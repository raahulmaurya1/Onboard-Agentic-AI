import React from 'react';
import styles from './ChatbotOrchestrator.module.css';

export default function DecisionView({ title, description, sessionUlid }) {
  return (
    <div className={styles.finalView}>
      <h2 className={styles.viewTitle}>{title}</h2>
      <p className={styles.agentMessage}>{description}</p>
      <p className={styles.metaText}>Your official Acknowledgement Number is: {sessionUlid || 'not-assigned'}</p>
    </div>
  );
}
