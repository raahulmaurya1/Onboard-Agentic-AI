import React from 'react';
import styles from './ChatbotOrchestrator.module.css';

export default function FinalDashboardView({ agentMessage, sessionUlid }) {
  return (
    <div className={styles.finalView}>
      <h2 className={styles.viewTitle}>Account Opened Successfully</h2>
      <p className={styles.agentMessage}>
        {agentMessage || 'Your onboarding is complete. Welcome to Onboard AI.'}
      </p>
      <p className={styles.metaText}> {sessionUlid || 'not-assigned'}</p>
    </div>
  );
}
