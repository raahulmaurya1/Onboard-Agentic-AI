import React from 'react';
import styles from './ProgressStepper.module.css';

// ── Step Definitions ─────────────────────────────────────────────────────────
const STEPS = [
  {
    id: 'identity',
    title: 'Verify Identity',
    actions: ['RENDER_CHAT', 'RENDER_PHONE_AUTH', 'RENDER_EMAIL_AUTH'],
  },
  {
    id: 'documents',
    title: 'Upload Documents',
    actions: ['RENDER_KYC_UPLOAD', 'RENDER_PROCESSING', 'RENDER_DATA_REVIEW'],
  },
  {
    id: 'face',
    title: 'Face Verification',
    actions: ['RENDER_FACE_VERIFICATION'],
  },
  {
    id: 'info',
    title: 'Additional Info',
    actions: ['RENDER_ADDITIONAL_INFO', 'RENDER_ADDITIONAL_INFO_FORM', 'RENDER_FINAL_REVIEW'],
  },
  {
    id: 'complete',
    title: 'Complete',
    actions: [
      'RENDER_AUTO_APPROVE',
      'RENDER_SUCCESS',
      'RENDER_HUMAN_REVIEW',
      'RENDER_FINAL_DASHBOARD',
    ],
  },
];

// ── Derive active step index from currentAction ───────────────────────────────
function getActiveStepIndex(currentAction) {
  const action = (currentAction || '').trim().toUpperCase();
  const idx = STEPS.findIndex((step) => step.actions.includes(action));
  return idx === -1 ? 0 : idx;
}

// ── Checkmark SVG ─────────────────────────────────────────────────────────────
function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path
        d="M2.5 7.5L5.5 10.5L11.5 3.5"
        stroke="#ffffff"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// ── Dot SVG (for active / upcoming) ──────────────────────────────────────────
function DotIcon({ filled }) {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
      <circle cx="5" cy="5" r="4" fill={filled ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function ProgressStepper({ currentAction }) {
  const activeIdx = getActiveStepIndex(currentAction);

  return (
    <aside className={styles.sidebar} aria-label="Onboarding progress">
      <nav className={styles.stepper}>
        {STEPS.map((step, idx) => {
          const isCompleted = idx < activeIdx;
          const isActive = idx === activeIdx;
          const isUpcoming = idx > activeIdx;
          const isLast = idx === STEPS.length - 1;

          return (
            <div key={step.id} className={styles.stepRow}>
              {/* Icon + connector column */}
              <div className={styles.iconCol}>
                {/* Circle icon */}
                <div
                  className={[
                    styles.circle,
                    isCompleted ? styles.circleCompleted : '',
                    isActive ? styles.circleActive : '',
                    isUpcoming ? styles.circleUpcoming : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                  aria-current={isActive ? 'step' : undefined}
                >
                  {isCompleted ? (
                    <CheckIcon />
                  ) : (
                    <DotIcon filled={isActive} />
                  )}
                </div>

                {/* Vertical connector line (not for last step) */}
                {!isLast && (
                  <div
                    className={[
                      styles.connector,
                      isCompleted ? styles.connectorDone : styles.connectorPending,
                    ].join(' ')}
                  />
                )}
              </div>

              {/* Step title */}
              <div className={styles.labelCol}>
                <span
                  className={[
                    styles.title,
                    isCompleted ? styles.titleCompleted : '',
                    isActive ? styles.titleActive : '',
                    isUpcoming ? styles.titleUpcoming : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                >
                  {step.title}
                </span>
              </div>
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
