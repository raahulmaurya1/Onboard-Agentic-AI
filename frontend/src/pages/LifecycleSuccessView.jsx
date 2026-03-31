import React from 'react';
import styles from './ChatbotOrchestrator.module.css';

export default function LifecycleSuccessView({ message, onDone }) {
  return (
    <div className={styles.finalView}>
      <h2 className={styles.viewTitle}>Update Completed</h2>
      <p className={styles.agentMessage}>
        {message || 'Your profile update has been completed successfully.'}
      </p>
      <button type="button" className={styles.primaryBtn} onClick={onDone}>
        Return to Home
      </button>
    </div>
  );
}
