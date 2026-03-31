import React, { useEffect, useState } from 'react';

/**
 * LoadingScreen
 * - Plays animated_video.svg fullscreen for ~4 seconds (0.5x perceived speed
 *   since we hold it twice as long as the animation's natural 2s duration)
 * - Fades out, then calls onComplete so App reveals the home page
 */
export default function LoadingScreen({ onComplete }) {
  const [fadeOut, setFadeOut] = useState(false);

  useEffect(() => {
    // Start fade-out at 3.5s
    const fadeTimer = setTimeout(() => setFadeOut(true), 1800);
    // Remove loading screen at 4.2s
    const doneTimer = setTimeout(() => onComplete(), 2200);

    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(doneTimer);
    };
  }, [onComplete]);

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        background: '#000',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        opacity: fadeOut ? 0 : 1,
        transition: 'opacity 0.7s ease',
        pointerEvents: fadeOut ? 'none' : 'all',
      }}
    >
      {/*
        We use <img> tag pointing to the SVG file in /public.
        The SVG has built-in SMIL animations; we hold it on screen
        for 4s to simulate 0.5× playback speed of the ~2s loop.
      */}
      <img
        src={`${process.env.PUBLIC_URL}/animated_video.svg`}
        alt="OnboardAI Loading"
        style={{
          width: '100vw',
          height: '100vh',
          objectFit: 'cover',
        }}
      />
    </div>
  );
}
