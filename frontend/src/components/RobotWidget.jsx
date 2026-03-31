import React, { useState } from 'react';
import styles from './RobotWidget.module.css';

/**
 * RobotWidget
 * Floating animated robot GIF pinned to the bottom-right corner.
 * Click the robot to open a small tooltip bubble.
 * Pass onGetStarted to open the onboarding chat.
 */
export default function RobotWidget({ onGetStarted }) {
  const [bubbleOpen, setBubbleOpen] = useState(false);

  const handleClick = () => setBubbleOpen((prev) => !prev);

  return (
    <div className={styles.wrapper}>
      {/* Speech bubble */}
      {bubbleOpen && (
        <div className={styles.bubble}>
          <p className={styles.bubbleText}>
            Hi! 👋 I'm OnboardAI.<br />
            Ready to open your account?
          </p>
          <button
            className={styles.bubbleBtn}
            onClick={() => {
              setBubbleOpen(false);
              onGetStarted();
            }}
          >
            Get Started →
          </button>
          <button
            className={styles.bubbleClose}
            onClick={() => setBubbleOpen(false)}
            aria-label="Close"
          >
            ✕
          </button>
          {/* Tail */}
          <div className={styles.tail} />
        </div>
      )}

      {/* Robot GIF button */}
      <button
        className={styles.robot}
        onClick={handleClick}
        aria-label="Open chat assistant"
        title="Chat with Luna"
      >
        <img
          src={`${process.env.PUBLIC_URL}/robot.gif`}
          alt="Luna AI assistant"
          className={styles.gif}
        />
        {/* Pulse ring */}
        <span className={styles.pulse} />
      </button>
    </div>
  );
}
