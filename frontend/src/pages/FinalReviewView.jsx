import React, { useEffect, useMemo, useState } from 'react';
import styles from './ChatbotOrchestrator.module.css';

function toLabel(key) {
  return String(key || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function stringifyValue(value) {
  if (value == null || value === '') return 'Not provided';
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function normalizeInitialDraft(data) {
  if (!data || typeof data !== 'object') {
    return {};
  }
  return Object.entries(data).reduce((acc, [key, value]) => {
    if (value == null) {
      acc[key] = '';
      return acc;
    }
    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
      acc[key] = String(value);
      return acc;
    }
    try {
      acc[key] = JSON.stringify(value);
    } catch {
      acc[key] = String(value);
    }
    return acc;
  }, {});
}

function isLikelyDate(value) {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value);
}

function isYesNo(value) {
  return typeof value === 'string' && /^(yes|no)$/i.test(value);
}

export default function FinalReviewView({ agentMessage, finalData, isSubmitting, onSubmit }) {
  const [draftData, setDraftData] = useState({});

  useEffect(() => {
    setDraftData(normalizeInitialDraft(finalData));
  }, [finalData]);

  const entries = useMemo(() => Object.entries(draftData), [draftData]);
  const canSubmit = entries.length > 0 && typeof onSubmit === 'function';

  const handleChange = (key, nextValue) => {
    setDraftData((prev) => ({
      ...prev,
      [key]: nextValue,
    }));
  };

  const handleSubmit = () => {
    if (!canSubmit) return;
    onSubmit(draftData);
  };

  return (
    <div className={styles.viewCard}>
      <h2 className={styles.viewTitle}>Final Review</h2>
      <p className={styles.agentMessage}>
        {agentMessage || 'Thanks. We are performing final review of your submitted details.'}
      </p>

      {entries.length > 0 ? (
        <ul className={styles.finalReviewList}>
          {entries.map(([key, value]) => (
            <li className={styles.finalReviewItem} key={key}>
              <span className={styles.finalReviewKey}>{toLabel(key)}</span>
              {isYesNo(value) ? (
                <select
                  className={styles.finalReviewInput}
                  value={String(value)}
                  onChange={(event) => handleChange(key, event.target.value)}
                  disabled={isSubmitting}
                >
                  <option value="Yes">Yes</option>
                  <option value="No">No</option>
                </select>
              ) : (
                <input
                  className={styles.finalReviewInput}
                  type={isLikelyDate(value) ? 'date' : 'text'}
                  value={stringifyValue(value)}
                  onChange={(event) => handleChange(key, event.target.value)}
                  disabled={isSubmitting}
                />
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className={styles.metaText}>Submitted data will appear here once received.</p>
      )}

      <div className={styles.finalReviewActions}>
        <button
          type="button"
          className={styles.primaryBtn}
          onClick={handleSubmit}
          disabled={!canSubmit || isSubmitting}
        >
          {isSubmitting ? 'Submitting...' : 'Submit Details'}
        </button>
      </div>

      <p className={styles.metaText}>Please keep this page open while we complete the final checks.</p>
    </div>
  );
}
