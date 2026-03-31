import React, { useCallback, useEffect, useRef, useState } from 'react';
import { fetchFaceVerificationStatus, submitFaceVerification } from './orchestratorApi';
import styles from './FaceVerificationView.module.css';

const POLL_INTERVAL_MS = 2500;
const MAX_POLL_ATTEMPTS = 30;
const RECORD_DURATION_MS = 3000;
const MIN_RECORD_DURATION_MS = 3000;
const RECORD_SECONDS = Math.floor(RECORD_DURATION_MS / 1000);

function sleep(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function getCameraErrorMessage(error) {
  const errorName = String(error?.name || '').toLowerCase();
  if (errorName === 'notallowederror' || errorName === 'securityerror') {
    return 'Camera access denied';
  }
  if (errorName === 'notfounderror' || errorName === 'overconstrainederror') {
    return 'No suitable front camera was found on this device.';
  }
  if (errorName === 'notreadableerror' || errorName === 'aborterror') {
    return 'Camera is busy in another app. Close other apps using the camera and retry.';
  }
  return 'Unable to access camera right now. Please retry in a moment.';
}

function resolveRecorderMimeType() {
  if (typeof window.MediaRecorder === 'undefined' || typeof window.MediaRecorder.isTypeSupported !== 'function') {
    return '';
  }
  const candidates = [
    'video/webm;codecs=vp9',
    'video/webm;codecs=vp8',
    'video/webm',
    'video/mp4',
  ];
  return candidates.find((type) => window.MediaRecorder.isTypeSupported(type)) || '';
}

function resolveFailureMessage(payload) {
  const candidates = [
    payload?.failure_reason,
    payload?.error_detail,
    payload?.error_message,
    payload?.reason,
    payload?.message,
    payload?.detail,
  ];
  const found = candidates.find((entry) => typeof entry === 'string' && entry.trim());
  return found ? found.trim() : 'Face mismatch or liveness check failed. Please retry.';
}

async function convertImageToJpeg(file) {
  if (!(file instanceof File)) {
    throw new Error('Invalid image file.');
  }
  if (file.type === 'image/jpeg') {
    return file;
  }

  const sourceUrl = URL.createObjectURL(file);
  try {
    const image = await new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error('Unable to read selected image.'));
      img.src = sourceUrl;
    });

    const canvas = document.createElement('canvas');
    canvas.width = image.width;
    canvas.height = image.height;
    const context = canvas.getContext('2d');
    if (!context) {
      throw new Error('Unable to process selected image.');
    }
    context.drawImage(image, 0, 0, canvas.width, canvas.height);

    const jpegBlob = await new Promise((resolve) => {
      canvas.toBlob(resolve, 'image/jpeg', 0.92);
    });
    if (!jpegBlob) {
      throw new Error('Unable to convert selected image to JPEG.');
    }

    const baseName = file.name.replace(/\.[^/.]+$/, '') || 'live_photo';
    return new File([jpegBlob], `${baseName}.jpg`, { type: 'image/jpeg' });
  } finally {
    URL.revokeObjectURL(sourceUrl);
  }
}

const INITIAL_RESULT = { type: '', message: '', detail: '' };

export default function FaceVerificationView({ agentMessage, sessionUlid, onVerificationSuccess }) {
  const [step, setStep] = useState('capture');
  const [photoMode, setPhotoMode] = useState('camera');
  const [cameraError, setCameraError] = useState('');
  const [, setHelperText] = useState('');
  const [isEnablingCamera, setIsEnablingCamera] = useState(false);
  const [isCameraEnabled, setIsCameraEnabled] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordCountdown, setRecordCountdown] = useState(RECORD_SECONDS);
  const [livePhotoFile, setLivePhotoFile] = useState(null);
  const [liveVideoFile, setLiveVideoFile] = useState(null);
  const [livePhotoPreviewUrl, setLivePhotoPreviewUrl] = useState('');
  const [liveVideoPreviewUrl, setLiveVideoPreviewUrl] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [verifyingText, setVerifyingText] = useState('Running liveness and face-match checks...');
  const [result, setResult] = useState(INITIAL_RESULT);
  const [isContinuing, setIsContinuing] = useState(false);

  const captureVideoRef = useRef(null);
  const recordVideoRef = useRef(null);
  const captureCanvasRef = useRef(null);
  const fileInputRef = useRef(null);
  const streamRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const mediaChunksRef = useRef([]);
  const recordStartedAtRef = useRef(0);
  const recordTimeoutRef = useRef(null);
  const countdownIntervalRef = useRef(null);
  const mountedRef = useRef(true);
  const cancelPollingRef = useRef(false);

  const hasAllMedia = Boolean(livePhotoFile && liveVideoFile);

  const attachStreamToVideos = useCallback((stream) => {
    [captureVideoRef.current, recordVideoRef.current]
      .filter(Boolean)
      .forEach((videoElement) => {
        try {
          videoElement.muted = true;
          videoElement.autoplay = true;
          videoElement.playsInline = true;
          // Only reassign if it's not already playing the right stream to prevent flickering
          if (videoElement.srcObject !== stream) {
            videoElement.srcObject = stream;
          }
          const playPromise = videoElement.play();
          if (playPromise && typeof playPromise.catch === 'function') {
            playPromise.catch(() => {});
          }
        } catch {
          // Keep attempting on other video nodes.
        }
      });
  }, []);

  // FIX: This ensures if you swap between "Upload" and "Camera" modes, 
  // the video element immediately reconnects to the active camera stream.
  useEffect(() => {
    if (streamRef.current && isCameraEnabled) {
      attachStreamToVideos(streamRef.current);
    }
  }, [photoMode, attachStreamToVideos, isCameraEnabled]);

  const clearRecordTimers = useCallback(() => {
    if (recordTimeoutRef.current !== null) {
      window.clearTimeout(recordTimeoutRef.current);
      recordTimeoutRef.current = null;
    }
    if (countdownIntervalRef.current !== null) {
      window.clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }
  }, []);

  const stopCamera = useCallback(() => {
    const activeRecorder = mediaRecorderRef.current;
    if (activeRecorder && activeRecorder.state !== 'inactive') {
      activeRecorder.stop();
    }
    mediaRecorderRef.current = null;
    mediaChunksRef.current = [];
    clearRecordTimers();

    const activeStream = streamRef.current;
    if (activeStream) {
      activeStream.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    [captureVideoRef.current, recordVideoRef.current].forEach((videoElement) => {
      if (videoElement) {
        videoElement.srcObject = null;
      }
    });

    if (mountedRef.current) {
      setIsCameraEnabled(false);
      setIsRecording(false);
      setRecordCountdown(RECORD_SECONDS);
    }
  }, [clearRecordTimers]);

  const enableCamera = useCallback(async () => {
    if (streamRef.current) {
      const hasLiveTrack = streamRef.current
        .getVideoTracks()
        .some((track) => track.readyState === 'live');
      if (hasLiveTrack) {
        setIsCameraEnabled(true);
        attachStreamToVideos(streamRef.current);
        return streamRef.current;
      }
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    if (!navigator?.mediaDevices?.getUserMedia) {
      setCameraError('This browser does not support camera capture. Please ensure you are on a secure connection (HTTPS or localhost).');
      return null;
    }

    setIsEnablingCamera(true);
    setCameraError('');
    setHelperText('');

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user' },
        audio: false,
      });
      if (!mountedRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return null;
      }
      streamRef.current = stream;
      setIsCameraEnabled(true);
      attachStreamToVideos(stream);
      return stream;
    } catch (error) {
      if (mountedRef.current) {
        setCameraError(getCameraErrorMessage(error));
      }
      return null;
    } finally {
      if (mountedRef.current) {
        setIsEnablingCamera(false);
      }
    }
  }, [attachStreamToVideos]);

  const captureLivePhoto = useCallback(async () => {
    setCameraError('');
    setHelperText('');

    const stream = await enableCamera();
    if (!stream) return;

    // Force attach right before capture to be absolutely certain
    const videoElement = captureVideoRef.current || recordVideoRef.current;
    if (videoElement && videoElement.srcObject !== stream) {
        videoElement.srcObject = stream;
        try { await videoElement.play(); } catch(e) {}
    }

    const canvas = captureCanvasRef.current;

    if (!videoElement || !canvas) {
      setCameraError('Internal error. Please refresh and try again.');
      return;
    }

    // FIX: Wait a tiny bit if the video is still booting up so we don't get a blank frame
    if (videoElement.readyState < 2) {
       await new Promise((resolve) => setTimeout(resolve, 300));
    }

    if (videoElement.readyState < 2) {
      setCameraError('Camera feed is not ready. Please wait a moment and click capture again.');
      return;
    }

    canvas.width = videoElement.videoWidth || 1280;
    canvas.height = videoElement.videoHeight || 720;
    const context = canvas.getContext('2d');
    if (!context) {
      setCameraError('Unable to process photo right now.');
      return;
    }

    context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setCameraError('Photo capture failed. Please try again.');
          return;
        }
        const file = new File([blob], `live_photo_${Date.now()}.jpg`, { type: 'image/jpeg' });
        if (!mountedRef.current) return;
        setLivePhotoFile(file);
        setHelperText('Live photo captured successfully.');
      },
      'image/jpeg',
      0.92
    );
  }, [enableCamera]);

  const handlePhotoUpload = useCallback(async (event) => {
    const inputElement = event.target;
    const selectedFile = inputElement?.files?.[0] || null;
    
    if (!selectedFile) {
      if (inputElement) inputElement.value = '';
      return;
    }

    const isImageByType = typeof selectedFile.type === 'string' && selectedFile.type.startsWith('image/');
    const isImageByName = /\.(jpg|jpeg|png|webp|heic|heif)$/i.test(selectedFile.name || '');
    if (!isImageByType && !isImageByName) {
      setCameraError('Please upload an image file for live photo.');
      if (inputElement) inputElement.value = '';
      return;
    }

    setCameraError('');
    setHelperText('');
    setLivePhotoFile(selectedFile);
    setPhotoMode('upload');
    setHelperText('Photo uploaded successfully.');

    try {
      const jpegFile = await convertImageToJpeg(selectedFile);
      if (!mountedRef.current) return;
      setLivePhotoFile(jpegFile);
    } catch {
      // Keep previously stored original file as fallback.
    } finally {
      // Safely clear the input only after processing is done
      if (inputElement) {
        inputElement.value = '';
      }
    }
  }, []);

  const stopRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === 'inactive') return;

    const elapsed = Date.now() - recordStartedAtRef.current;
    if (elapsed < MIN_RECORD_DURATION_MS) {
      setHelperText('Please record at least 3 seconds to complete the liveness step.');
      return;
    }

    recorder.stop();
  }, []);

  const startRecording = useCallback(async () => {
    if (isRecording) return;
    setCameraError('');
    setHelperText('');

    if (typeof window.MediaRecorder === 'undefined') {
      setCameraError('This browser does not support live video recording.');
      return;
    }

    const stream = await enableCamera();
    if (!stream) return;

    const mimeType = resolveRecorderMimeType();
    try {
      mediaChunksRef.current = [];
      const recorder = mimeType ? new window.MediaRecorder(stream, { mimeType }) : new window.MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      recordStartedAtRef.current = Date.now();

      setIsRecording(true);
      setRecordCountdown(RECORD_SECONDS);

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          mediaChunksRef.current.push(event.data);
        }
      };

      recorder.onerror = () => {
        if (!mountedRef.current) return;
        setCameraError('Recording failed. Please retry.');
        setIsRecording(false);
        setRecordCountdown(RECORD_SECONDS);
        clearRecordTimers();
      };

      recorder.onstop = () => {
        clearRecordTimers();
        const recordedType = recorder.mimeType || mimeType || 'video/webm';
        const recordedBlob = new Blob(mediaChunksRef.current, { type: recordedType });
        mediaChunksRef.current = [];
        mediaRecorderRef.current = null;

        if (!mountedRef.current) return;
        setIsRecording(false);
        setRecordCountdown(RECORD_SECONDS);

        if (!recordedBlob.size) {
          setCameraError('Recorded video is empty. Please record again.');
          return;
        }

        const extension = recordedType.includes('mp4') ? 'mp4' : 'webm';
        const file = new File([recordedBlob], `live_video_${Date.now()}.${extension}`, {
          type: recordedType,
        });
        setLiveVideoFile(file);
        setHelperText('Live video captured. Great work.');
      };

      recorder.start(200);

      countdownIntervalRef.current = window.setInterval(() => {
        if (!mountedRef.current) return;
        setRecordCountdown((previous) => (previous > 1 ? previous - 1 : 1));
      }, 1000);

      recordTimeoutRef.current = window.setTimeout(() => {
        const activeRecorder = mediaRecorderRef.current;
        if (activeRecorder && activeRecorder.state !== 'inactive') {
          activeRecorder.stop();
        }
      }, RECORD_DURATION_MS);
    } catch {
      if (!mountedRef.current) return;
      setCameraError('Unable to start recording. Please retry.');
      setIsRecording(false);
      setRecordCountdown(RECORD_SECONDS);
      clearRecordTimers();
    }
  }, [clearRecordTimers, enableCamera, isRecording]);

  const pollForVerificationResult = useCallback(async (activeSessionUlid) => {
    for (let attempt = 0; attempt < MAX_POLL_ATTEMPTS; attempt += 1) {
      if (cancelPollingRef.current) {
        throw new Error('Verification polling cancelled.');
      }

      try {
        const payload = await fetchFaceVerificationStatus(activeSessionUlid);
        const status = String(payload?.status || '').trim().toLowerCase();

        if (status === 'processing' || status === 'pending' || status === 'queued') {
          if (mountedRef.current) {
            setVerifyingText(
              attempt % 2 === 0
                ? 'Running liveness and face-match checks...'
                : 'Still verifying. Please keep this window open.'
            );
          }
          await sleep(POLL_INTERVAL_MS);
          continue;
        }

        return payload;
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        const isTransient = /\((404|202|204|429|500|502|503|504)\)/.test(message);
        if (!isTransient || attempt === MAX_POLL_ATTEMPTS - 1) {
          throw error;
        }
        await sleep(POLL_INTERVAL_MS);
      }
    }

    throw new Error('Verification is taking longer than expected. Please retry.');
  }, []);

  const submitForVerification = useCallback(async () => {
    if (isSubmitting) return;

    const activeSessionUlid = typeof sessionUlid === 'string' ? sessionUlid.trim() : '';
    if (!activeSessionUlid) {
      setCameraError('Session is missing. Please restart onboarding and try again.');
      return;
    }
    if (!livePhotoFile || !liveVideoFile) {
      setCameraError('Please provide both a live photo and a live video before submitting.');
      return;
    }

    cancelPollingRef.current = false;
    setIsSubmitting(true);
    setResult(INITIAL_RESULT);
    setCameraError('');
    setHelperText('');
    setVerifyingText('Running liveness and face-match checks...');
    setStep('verifying');
    setIsContinuing(false);
    stopCamera();

    try {
      await submitFaceVerification({
        sessionUlid: activeSessionUlid,
        livePhoto: livePhotoFile,
        liveVideo: liveVideoFile,
      });

      const statusPayload = await pollForVerificationResult(activeSessionUlid);
      if (cancelPollingRef.current || !mountedRef.current) return;

      const status = String(statusPayload?.status || '').trim().toLowerCase();
      const verdict = statusPayload?.overall_verdict === true;

      if (status === 'success' && verdict) {
        setResult({
          type: 'success',
          message: 'Face verification completed successfully.',
          detail: 'Secure handoff in progress...',
        });
        setStep('result');
        setIsContinuing(true);

        if (typeof onVerificationSuccess === 'function') {
          try {
            await onVerificationSuccess();
          } catch (error) {
            if (!mountedRef.current) return;
            const continueError = error instanceof Error
              ? error.message
              : 'Could not continue to the next step.';
            setIsContinuing(false);
            setResult({
              type: 'error',
              message: 'Verification passed, but automatic transition failed.',
              detail: continueError,
            });
          }
        }
        return;
      }

      if (status === 'success' && !verdict) {
        setResult({
          type: 'failure',
          message: 'We could not verify your identity.',
          detail: resolveFailureMessage(statusPayload),
        });
        setStep('result');
        return;
      }

      if (status === 'error') {
        setResult({
          type: 'error',
          message: 'Face verification service returned an error.',
          detail: resolveFailureMessage(statusPayload),
        });
        setStep('result');
        return;
      }

      setResult({
        type: 'error',
        message: 'Unexpected verification response.',
        detail: resolveFailureMessage(statusPayload),
      });
      setStep('result');
    } catch (error) {
      if (cancelPollingRef.current || !mountedRef.current) return;
      const message = error instanceof Error ? error.message : 'Unable to complete face verification.';
      setResult({
        type: 'error',
        message: 'Could not complete face verification.',
        detail: message,
      });
      setStep('result');
    } finally {
      if (mountedRef.current) {
        setIsSubmitting(false);
      }
    }
  }, [
    isSubmitting,
    livePhotoFile,
    liveVideoFile,
    onVerificationSuccess,
    pollForVerificationResult,
    sessionUlid,
    stopCamera,
  ]);

  useEffect(() => {
    if (!livePhotoFile) {
      setLivePhotoPreviewUrl('');
      return undefined;
    }
    const nextUrl = URL.createObjectURL(livePhotoFile);
    setLivePhotoPreviewUrl(nextUrl);
    return () => URL.revokeObjectURL(nextUrl);
  }, [livePhotoFile]);

  useEffect(() => {
    if (!liveVideoFile) {
      setLiveVideoPreviewUrl('');
      return undefined;
    }
    const nextUrl = URL.createObjectURL(liveVideoFile);
    setLiveVideoPreviewUrl(nextUrl);
    return () => URL.revokeObjectURL(nextUrl);
  }, [liveVideoFile]);

  useEffect(() => {
    if (step !== 'capture') {
      stopCamera();
    }
  }, [step, stopCamera]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      cancelPollingRef.current = true;
      stopCamera();
    };
  }, [stopCamera]);

  const handleCaptureAgain = () => {
    cancelPollingRef.current = true;
    setResult(INITIAL_RESULT);
    setIsContinuing(false);
    setStep('capture');
    setCameraError('');
    setHelperText('');
    setIsSubmitting(false);
    setLivePhotoFile(null);
    setLiveVideoFile(null);
  };

  const handleRetryWithCurrentMedia = () => {
    if (!hasAllMedia) {
      setStep('capture');
      return;
    }
    void submitForVerification();
  };

  return (
    <section className={styles.faceWrap}>
      <div className={styles.headerPanel}>
        <div>
          <h2 className={styles.title}>Face Verification</h2>
          <p className={styles.subtitle}>
            {agentMessage || 'Capture a live photo and a short liveness video to continue onboarding.'}
          </p>
        </div>
        <div className={styles.sessionChip}>Session: {sessionUlid || 'not-assigned'}</div>
      </div>

      <div className={styles.stepRail}>
        <span className={`${styles.stepDot} ${step === 'capture' ? styles.stepDotActive : ''}`}>1 Capture</span>
        <span className={`${styles.stepDot} ${step === 'result' ? styles.stepDotActive : ''}`}>2 Result</span>
      </div>

      <div className={styles.stageShell}>
        {step === 'capture' && (
          <div className={`${styles.captureGrid} ${styles.captureGridExpanded}`}>
            <article className={`${styles.glassCard} ${styles.photoCard}`}>
              <div className={styles.cardHeader}>
                <h3>Live Photo</h3>
                <div className={styles.modeSwitch}>
                  <button
                    type="button"
                    className={`${styles.modeBtn} ${photoMode === 'camera' ? styles.modeBtnActive : ''}`}
                    onClick={() => setPhotoMode('camera')}
                  >
                    Camera
                  </button>
                  <button
                    type="button"
                    className={`${styles.modeBtn} ${photoMode === 'upload' ? styles.modeBtnActive : ''}`}
                    onClick={() => setPhotoMode('upload')}
                  >
                    Upload
                  </button>
                </div>
              </div>

              {photoMode === 'camera' ? (
                <>
                  <div className={styles.cameraCircle}>
                    <video
                      ref={captureVideoRef}
                      className={styles.cameraFeed}
                      autoPlay
                      playsInline
                      muted
                    />
                    {!isCameraEnabled && (
                      <div className={styles.cameraPlaceholder}>
                        <span>Enable camera to capture a clear forward-facing selfie</span>
                      </div>
                    )}
                  </div>

                  <div className={styles.actionRow}>
                    <button
                      type="button"
                      className={styles.ghostBtn}
                      onClick={() => {
                        void enableCamera();
                      }}
                      disabled={isEnablingCamera || isSubmitting}
                    >
                      {isEnablingCamera ? 'Enabling...' : 'Enable Camera'}
                    </button>
                    <button
                      type="button"
                      className={styles.primaryBtn}
                      onClick={() => {
                        void captureLivePhoto();
                      }}
                      disabled={isSubmitting}
                    >
                      Capture Photo
                    </button>
                  </div>
                </>
              ) : (
                <label className={styles.uploadDrop} htmlFor="live-photo-upload">
                  <input
                    ref={fileInputRef}
                    id="live-photo-upload"
                    type="file"
                    accept="image/*"
                    onChange={(event) => {
                      void handlePhotoUpload(event);
                    }}
                    disabled={isSubmitting}
                  />
                  <span>Upload a clear JPEG selfie</span>
                </label>
              )}

              {livePhotoPreviewUrl && (
                <div className={styles.previewChip}>
                  <img src={livePhotoPreviewUrl} alt="Captured selfie" />
                  <button
                    type="button"
                    onClick={() => setLivePhotoFile(null)}
                    className={styles.linkBtn}
                    disabled={isSubmitting}
                  >
                    Retake
                  </button>
                </div>
              )}
            </article>

            <article className={`${styles.glassCard} ${styles.videoCard}`}>
              <div className={styles.cardHeader}>
                <h3>Live Video</h3>
                <span className={styles.blinkNote}>Blink naturally for 3-5 seconds</span>
              </div>

              <div className={styles.videoPreviewShell}>
                <video
                  ref={recordVideoRef}
                  className={styles.videoFeed}
                  autoPlay
                  playsInline
                  muted
                />
                {!isCameraEnabled && (
                  <div className={styles.videoPlaceholder}>
                    <span>Enable camera to record your liveness clip</span>
                  </div>
                )}
                {isRecording && <div className={styles.recordBadge}>REC {recordCountdown}s</div>}
              </div>

              <div className={styles.actionRow}>
                <button
                  type="button"
                  className={styles.ghostBtn}
                  onClick={() => {
                    void enableCamera();
                  }}
                  disabled={isEnablingCamera || isSubmitting}
                >
                  {isEnablingCamera ? 'Enabling...' : 'Enable Camera'}
                </button>
                {!isRecording ? (
                  <button
                    type="button"
                    className={styles.primaryBtn}
                    onClick={() => {
                      void startRecording();
                    }}
                    disabled={isSubmitting}
                  >
                    Record 3s
                  </button>
                ) : (
                  <button
                    type="button"
                    className={styles.primaryBtn}
                    onClick={stopRecording}
                    disabled={isSubmitting}
                  >
                    Stop
                  </button>
                )}
              </div>

              {liveVideoPreviewUrl && (
                <div className={styles.previewChip}>
                  <video src={liveVideoPreviewUrl} className={styles.videoThumb} controls preload="metadata" />
                  <button
                    type="button"
                    onClick={() => setLiveVideoFile(null)}
                    className={styles.linkBtn}
                    disabled={isSubmitting || isRecording}
                  >
                    Re-record
                  </button>
                </div>
              )}
            </article>

            <div 
              className={styles.bottomAction} 
              style={{ 
                gridColumn: '1 / -1', 
                display: 'flex', 
                justifyContent: 'flex-end', 
                marginTop: '1rem',
                paddingBottom: '1rem'
              }}
            >
              <button
                type="button"
                className={styles.primaryBtn}
                onClick={() => { void submitForVerification(); }}
                disabled={!hasAllMedia || isSubmitting || isRecording}
              >
                Submit Verification
              </button>
            </div>
          </div>
        )}

        {step === 'verifying' && (
          <div className={`${styles.glassCard} ${styles.verifyingCard}`} role="status" aria-live="polite">
            <div className={styles.verifyingSpinner} aria-hidden="true" />
            <h3>Verifying Identity</h3>
            <p>{verifyingText}</p>
          </div>
        )}

        {step === 'result' && (
          <div className={`${styles.glassCard} ${styles.resultCard}`}>
            <div className={`${styles.resultIcon} ${result.type === 'success' ? styles.ok : styles.fail}`}>
              {result.type === 'success' ? '✓' : '!'}
            </div>
            <h3>{result.message || 'Verification update'}</h3>
            {result.detail && <p>{result.detail}</p>}

            {result.type === 'success' && isContinuing ? (
              <div className={styles.continueText}>Transitioning to the next onboarding step...</div>
            ) : (
              <div className={styles.actionRow}>
                <button
                  type="button"
                  className={styles.primaryBtn}
                  onClick={handleRetryWithCurrentMedia}
                  disabled={!hasAllMedia || isSubmitting}
                >
                  Retry
                </button>
                <button
                  type="button"
                  className={styles.ghostBtn}
                  onClick={handleCaptureAgain}
                  disabled={isSubmitting}
                >
                  Capture Again
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {cameraError && <div className={styles.errorText}>{cameraError}</div>}

      <canvas ref={captureCanvasRef} className={styles.hiddenCanvas} />
    </section>
  );
}