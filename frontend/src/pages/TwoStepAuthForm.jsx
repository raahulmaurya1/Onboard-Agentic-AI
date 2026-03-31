import React, { useCallback, useEffect, useRef, useState } from 'react';
import styles from './ChatbotOrchestrator.module.css';

const OTP_MAX_SEND_ATTEMPTS = 3;
const OTP_VALIDITY_SECONDS = 180;
const OTP_LOCK_SECONDS = 300;

const COPY_BY_MODE = {
  phone: {
    title: 'Phone Authentication',
    description:
      "Great! Let's start by verifying your phone number. Please enter your mobile number.",
    requiredLabel: 'phone',
    contactLabel: 'Phone Number',
    contactPlaceholder: 'Enter phone number with country code +91XXXXXXXXXX',
    editText: 'Edit number',
  },
  email: {
    title: 'Email Authentication',
    description: "Great! Let's verify your email address. Please enter your email to continue.",
    requiredLabel: 'email',
    contactLabel: 'Email Address',
    contactPlaceholder: 'name@example.com',
    editText: 'Edit email',
  },
};

function formatDuration(totalSeconds) {
  const safeSeconds = Math.max(0, totalSeconds);
  const minutes = String(Math.floor(safeSeconds / 60)).padStart(2, '0');
  const seconds = String(safeSeconds % 60).padStart(2, '0');
  return `${minutes}:${seconds}`;
}

function defaultOtpPolicy() {
  return {
    attempts: 0,
    otpExpiresAt: 0,
    lockoutUntil: 0,
  };
}

export default function TwoStepAuthForm({
  mode,
  agentMessage,
  dataRequired,
  initialState,
  isSubmitting,
  onSendOtp,
  onVerifyOtp,
}) {
  const copy = COPY_BY_MODE[mode] || COPY_BY_MODE.phone;
  const [contactValue, setContactValue] = useState('');
  const [submittedContact, setSubmittedContact] = useState('');
  const [otpDisplayContact, setOtpDisplayContact] = useState('');
  const [otpValue, setOtpValue] = useState('');
  const [isOtpSent, setIsOtpSent] = useState(false);
  const [otpErrorText, setOtpErrorText] = useState('');
  const [activeContactKey, setActiveContactKey] = useState('');
  const [otpPolicyByContact, setOtpPolicyByContact] = useState({});
  const [nowTs, setNowTs] = useState(Date.now());
  const [countryCode, setCountryCode] = useState('US');

  const contactInputRef = useRef(null);
  const otpInputRef = useRef(null);
  const otpBoxRefs = useRef([]);
  const lastAppliedInitSignatureRef = useRef('');

  const normalizedDataRequired = Array.isArray(dataRequired)
    ? dataRequired
      .map((field) => (typeof field === 'string' ? field.trim().toLowerCase() : ''))
      .filter(Boolean)
    : [];
  const isOtpRequestedByBackend = useCallback(
    (fields) => (
      Array.isArray(fields)
      && fields.some(
        (field) => typeof field === 'string' && field.trim().toLowerCase().includes('otp')
      )
    ),
    []
  );
  const otpRequestedByBackend = isOtpRequestedByBackend(normalizedDataRequired);
  const isOtpOnlyRequired = normalizedDataRequired.length === 1 && normalizedDataRequired[0] === 'otp';
  const shouldRenderOtpStep = isOtpSent || isOtpOnlyRequired || otpRequestedByBackend;

  const isOtpSendSuccessMessage = (message) =>
    typeof message === 'string'
    && /\botp\b[\s\S]{0,60}\bsent\b|\bsent\b[\s\S]{0,60}\botp\b/i.test(message);

  const normalizeContactValue = useCallback((value) => {
    const trimmed = value.trim();
    if (!trimmed) return '';
    if (mode === 'email') return trimmed.toLowerCase();
    return trimmed.replace(/\s+/g, '');
  }, [mode]);

  const resolvePolicy = useCallback((rawPolicy, referenceTime) => {
    const policy = rawPolicy || defaultOtpPolicy();
    if (policy.lockoutUntil > 0 && referenceTime >= policy.lockoutUntil) {
      return defaultOtpPolicy();
    }
    return policy;
  }, []);

  useEffect(() => {
    if (shouldRenderOtpStep) return;
    setOtpValue('');
    if (otpInputRef.current) {
      otpInputRef.current.setCustomValidity('');
    }
  }, [shouldRenderOtpStep]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setNowTs(Date.now());
    }, 1000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    const incomingInitState = initialState && typeof initialState === 'object'
      ? initialState
      : {};
    const shouldBootstrapOtp = (
      incomingInitState.isOtpSent === true
      || incomingInitState.is_otp_sent === true
      || isOtpOnlyRequired
    );
    if (!shouldBootstrapOtp) return;

    const incomingContact = typeof incomingInitState.contact === 'string'
      ? incomingInitState.contact.trim()
      : '';
    const fallbackSessionContact = typeof incomingInitState.sessionContact === 'string'
      ? incomingInitState.sessionContact.trim()
      : '';
    const resolvedContact = incomingContact || fallbackSessionContact || submittedContact.trim();
    const maskedContact = typeof incomingInitState.maskedContact === 'string'
      ? incomingInitState.maskedContact.trim()
      : '';
    const resolvedDisplayContact = maskedContact || resolvedContact;
    const parsedOtpExpiry = Number(incomingInitState.otpExpirySeconds);
    const otpExpirySeconds = Number.isFinite(parsedOtpExpiry) && parsedOtpExpiry > 0
      ? Math.ceil(parsedOtpExpiry)
      : OTP_VALIDITY_SECONDS;
    const initSignature = [
      mode,
      shouldBootstrapOtp ? '1' : '0',
      resolvedContact,
      resolvedDisplayContact,
      String(otpExpirySeconds),
    ].join('|');

    if (lastAppliedInitSignatureRef.current === initSignature) {
      return;
    }
    lastAppliedInitSignatureRef.current = initSignature;

    const now = Date.now();
    const normalizedResolvedContact =
      normalizeContactValue(resolvedContact) || `bootstrap_${mode}_contact`;
    if (resolvedContact) {
      setContactValue(resolvedContact);
      setSubmittedContact(resolvedContact);
    }
    setOtpDisplayContact(resolvedDisplayContact);
    setIsOtpSent(true);
    setOtpValue('');
    setOtpErrorText('');
    setActiveContactKey(normalizedResolvedContact);
    setOtpPolicyByContact((prev) => {
      const existingPolicy = resolvePolicy(prev[normalizedResolvedContact], now);
      return {
        ...prev,
        [normalizedResolvedContact]: {
          attempts: existingPolicy.attempts,
          otpExpiresAt: now + otpExpirySeconds * 1000,
          lockoutUntil: existingPolicy.lockoutUntil > now ? existingPolicy.lockoutUntil : 0,
        },
      };
    });
    setNowTs(now);
  }, [
    initialState,
    isOtpOnlyRequired,
    mode,
    normalizeContactValue,
    resolvePolicy,
    submittedContact,
  ]);

  useEffect(() => {
    if (!shouldRenderOtpStep || !otpInputRef.current) return;
    const timeoutId = window.setTimeout(() => {
      otpInputRef.current?.focus();
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [shouldRenderOtpStep]);

  const currentInputContactKey = normalizeContactValue(contactValue);
  const currentInputPolicy = resolvePolicy(
    currentInputContactKey ? otpPolicyByContact[currentInputContactKey] : null,
    nowTs
  );
  const currentInputLockoutSeconds = Math.max(
    0,
    Math.ceil((currentInputPolicy.lockoutUntil - nowTs) / 1000)
  );

  const activePolicy = resolvePolicy(
    activeContactKey ? otpPolicyByContact[activeContactKey] : null,
    nowTs
  );
  const otpRemainingSeconds = Math.max(
    0,
    Math.ceil((activePolicy.otpExpiresAt - nowTs) / 1000)
  );
  const lockoutRemainingSeconds = Math.max(
    0,
    Math.ceil((activePolicy.lockoutUntil - nowTs) / 1000)
  );
  const otpExpired = shouldRenderOtpStep && otpRemainingSeconds === 0;
  const fallbackSessionContact =
    initialState && typeof initialState.sessionContact === 'string'
      ? initialState.sessionContact.trim()
      : '';
  const verificationContact = submittedContact.trim() || fallbackSessionContact;
  const hasSubmittedContact = verificationContact.length > 0;
  const otpRecipientText = otpDisplayContact || verificationContact || copy.requiredLabel;

  const validateContact = () => {
    if (!contactInputRef.current) return true;
    const value = contactValue.trim();

    if (mode === 'phone') {
      const isValidPhone = /^\+?[0-9][0-9\s()-]{6,18}$/.test(value);
      if (!isValidPhone) {
        contactInputRef.current.setCustomValidity('Please enter a valid phone number.');
        contactInputRef.current.reportValidity();
        return false;
      }
    } else {
      const isValidEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
      if (!isValidEmail) {
        contactInputRef.current.setCustomValidity('Please enter a valid email address.');
        contactInputRef.current.reportValidity();
        return false;
      }
    }

    contactInputRef.current.setCustomValidity('');
    return true;
  };

  const validateOtp = () => {
    if (!otpInputRef.current) return true;

    const isValidOtp = /^\d{6}$/.test(otpValue);
    if (!isValidOtp) {
      otpInputRef.current.setCustomValidity('Please enter the 6-digit OTP.');
      otpInputRef.current.reportValidity();
      return false;
    }

    otpInputRef.current.setCustomValidity('');
    return true;
  };

  const sendOtpForContact = async (displayContact) => {
    const normalizedContact = normalizeContactValue(displayContact);
    if (!normalizedContact) return;

    const now = Date.now();
    const currentPolicy = resolvePolicy(otpPolicyByContact[normalizedContact], now);
    const lockoutSeconds = Math.max(
      0,
      Math.ceil((currentPolicy.lockoutUntil - now) / 1000)
    );

    if (lockoutSeconds > 0) {
      setOtpErrorText(`OTP sending is locked. Try again in ${formatDuration(lockoutSeconds)}.`);
      return;
    }

    if (typeof onSendOtp !== 'function') return;

    try {
      setOtpErrorText('');
      const response = await onSendOtp({
        mode,
        contact: displayContact,
      });

      const backendAcceptedOtpSend =
        isOtpRequestedByBackend(response?.data_required)
        || isOtpSendSuccessMessage(response?.agent_message);
      if (!backendAcceptedOtpSend) {
        setOtpErrorText(
          response?.agent_message
            || 'Unable to send OTP right now. Please confirm the number and try again.'
        );
        return;
      }

      const nextAttempts = currentPolicy.attempts + 1;
      const nextPolicy = {
        attempts: nextAttempts,
        otpExpiresAt: now + OTP_VALIDITY_SECONDS * 1000,
        lockoutUntil:
          nextAttempts >= OTP_MAX_SEND_ATTEMPTS
            ? now + OTP_LOCK_SECONDS * 1000
            : 0,
      };

      setOtpPolicyByContact((prev) => ({
        ...prev,
        [normalizedContact]: nextPolicy,
      }));

      setNowTs(now);
      setSubmittedContact(displayContact);
      setOtpDisplayContact(displayContact);
      setActiveContactKey(normalizedContact);
      setOtpValue('');
      setIsOtpSent(true);
      setOtpErrorText('');
    } catch (error) {
      const message = error instanceof Error
        ? error.message
        : 'Unable to send OTP right now. Please try again.';
      setOtpErrorText(message);
    }
  };

  const handleSendOtp = async (event) => {
    event.preventDefault();
    if (!validateContact()) return;

    const countryPrefixMap = { US: '+1', IN: '+91' };
    const prefix = countryPrefixMap[countryCode] || '';
    const displayContact = mode === 'phone' ? `${prefix} ${contactValue.trim()}` : contactValue.trim();
    await sendOtpForContact(displayContact);
  };

  const handleResendOtp = async () => {
    if (!verificationContact) return;
    await sendOtpForContact(verificationContact);
  };

  const handleVerifyOtp = (event) => {
    event.preventDefault();
    if (!validateOtp()) return;
    if (otpExpired) {
      setOtpErrorText('OTP expired. Please request a new OTP.');
      return;
    }

    setOtpErrorText('');
    if (typeof onVerifyOtp === 'function') {
      onVerifyOtp({
        mode,
        contact: verificationContact,
        otp: otpValue,
      });
    }
  };

  const handleContactChange = (event) => {
    if (contactInputRef.current) {
      contactInputRef.current.setCustomValidity('');
    }
    setOtpErrorText('');
    setContactValue(event.target.value);
  };

  const handleOtpBoxChange = (index, newValue) => {
    const digit = newValue.replace(/\D/g, '').slice(-1);
    const newOtpArr = Array.from({ length: 6 }).map((_, i) => otpValue[i] || '');
    if (digit) {
       newOtpArr[index] = digit;
       setOtpValue(newOtpArr.join(''));
       if (index < 5) otpBoxRefs.current[index + 1]?.focus();
    } else {
       newOtpArr[index] = '';
       setOtpValue(newOtpArr.join(''));
    }
    if (otpInputRef.current) otpInputRef.current.setCustomValidity('');
  };

  const handleOtpBoxKeyDown = (index, event) => {
    if (event.key === 'Backspace' && !(otpValue[index] || '') && index > 0) {
      otpBoxRefs.current[index - 1]?.focus();
    }
  };

  const handleOtpBoxPaste = (event) => {
    event.preventDefault();
    const paste = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (!paste) return;
    setOtpValue(paste);
    if (otpInputRef.current) otpInputRef.current.setCustomValidity('');
    const nextIndex = Math.min(paste.length, 5);
    otpBoxRefs.current[nextIndex]?.focus();
  };

  const handleEdit = () => {
    setIsOtpSent(false);
    setOtpValue('');
    setOtpErrorText('');
    setOtpDisplayContact('');
    if (otpInputRef.current) {
      otpInputRef.current.setCustomValidity('');
    }
  };

  const otpBoxesData = Array.from({ length: 6 }).map((_, i) => otpValue[i] || '');

  return (
    <div className={styles.viewCard}>
      <h2 className={styles.viewTitle}>{copy.title}</h2>
      {/* <p className={styles.agentMessage}>{agentMessage || copy.description}</p> */}
      {/* <p className={styles.metaText}>Required: {dataRequired?.join(', ') || copy.requiredLabel}</p> */}
      {otpErrorText && <p className={styles.errorText}>{otpErrorText}</p>}

      {!shouldRenderOtpStep ? (
        <form className={styles.form} onSubmit={handleSendOtp} noValidate>
          <div>
            <label htmlFor={`${mode}-contact`} className={styles.label}>
              {copy.contactLabel}
            </label>
            
            {mode === 'phone' ? (
              <div className={styles.phoneInputWrapper}>
                <div className={styles.countrySelectWrapper}>
                  <select 
                    className={styles.countrySelect}
                    value={countryCode}
                    onChange={(e) => setCountryCode(e.target.value)}
                  >
                    <option value="US">US</option>
                    <option value="IN">IN</option>
                  </select>
                </div>
                <div className={styles.phoneDivider}></div>
                <input
                  ref={contactInputRef}
                  id={`${mode}-contact`}
                  name={`${mode}-contact`}
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  value={contactValue}
                  onChange={handleContactChange}
                  onInvalid={() => validateContact()}
                  placeholder="(555) 000-0000"
                  required
                  className={styles.phoneInput}
                />
                <div className={styles.phoneHelpIcon}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                  </svg>
                </div>
              </div>
            ) : (
              <div className={styles.emailInputWrapper}>
                <div className={styles.emailIcon}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="2" y="4" width="20" height="16" rx="2" ry="2"></rect>
                    <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"></path>
                  </svg>
                </div>
                <input
                  ref={contactInputRef}
                  id={`${mode}-contact`}
                  name={`${mode}-contact`}
                  type="email"
                  inputMode="email"
                  autoComplete="email"
                  value={contactValue}
                  onChange={handleContactChange}
                  onInvalid={() => validateContact()}
                  placeholder={copy.contactPlaceholder}
                  required
                  className={styles.emailInput}
                />
                <div className={styles.phoneHelpIcon}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                  </svg>
                </div>
              </div>
            )}
            {/* <p className={styles.inputHint}>Enter your Phone number/email.</p> */}
          </div>
          {currentInputLockoutSeconds > 0 && (
            <p className={styles.metaText}>
              Send locked for {formatDuration(currentInputLockoutSeconds)} after 3 attempts.
            </p>
          )}
          <button
            type="submit"
            disabled={isSubmitting || currentInputLockoutSeconds > 0}
            className={styles.primaryBtn}
          >
            {isSubmitting ? 'Submitting...' : 'Send OTP'}
          </button>
        </form>
      ) : (
        <form className={styles.form} onSubmit={handleVerifyOtp} noValidate>
          <p className={styles.agentMessage}>An OTP has been sent to {otpRecipientText}.</p>
          <p className={styles.metaText}>
            OTP valid for: {formatDuration(otpRemainingSeconds)}.
          </p>
          <p className={styles.metaText}>
            Send attempts used: {Math.min(activePolicy.attempts, OTP_MAX_SEND_ATTEMPTS)}/{OTP_MAX_SEND_ATTEMPTS}
          </p>
          {lockoutRemainingSeconds > 0 && (
            <p className={styles.metaText}>
              Resend locked for {formatDuration(lockoutRemainingSeconds)}.
            </p>
          )}
          <div>
            <div className={styles.secureCodeBadge}>Secure code</div>
            <div className={styles.otpBoxesWrapper}>
              {otpBoxesData.map((val, idx) => (
                <React.Fragment key={`otp-box-${idx}`}>
                  <input
                    ref={(el) => {
                      otpBoxRefs.current[idx] = el;
                      if (idx === 0) otpInputRef.current = el; // Plug into existing validation
                    }}
                    type="text"
                    inputMode="numeric"
                    maxLength={2}
                    value={val}
                    onChange={(e) => handleOtpBoxChange(idx, e.target.value)}
                    onKeyDown={(e) => handleOtpBoxKeyDown(idx, e)}
                    onPaste={handleOtpBoxPaste}
                    className={styles.otpBox}
                    placeholder="0"
                  />
                  {idx === 2 && <span className={styles.otpDash}>-</span>}
                </React.Fragment>
              ))}
            </div>
            {/* <p className={styles.inputHint}>Enter OTP received on your phone number/email.</p> */}
            
            {!isOtpOnlyRequired && (
              <button
                type="button"
                onClick={handleEdit}
                className={styles.metaText}
                style={{
                  textDecoration: 'underline',
                  background: 'none',
                  border: 'none',
                  padding: '4px 0 0',
                  cursor: 'pointer',
                  textAlign: 'left',
                  display: 'block',
                }}
              >
                {copy.editText}
              </button>
            )}
            <button
              type="button"
              onClick={handleResendOtp}
              className={styles.metaText}
              disabled={
                isSubmitting
                || otpRemainingSeconds > 0
                || lockoutRemainingSeconds > 0
                || !hasSubmittedContact
              }
              style={{
                textDecoration: 'underline',
                background: 'none',
                border: 'none',
                padding: '6px 0 0',
                cursor:
                  isSubmitting || otpRemainingSeconds > 0 || lockoutRemainingSeconds > 0 || !hasSubmittedContact
                    ? 'not-allowed'
                    : 'pointer',
                textAlign: 'left',
                display: 'block',
                opacity:
                  isSubmitting || otpRemainingSeconds > 0 || lockoutRemainingSeconds > 0 || !hasSubmittedContact
                    ? 0.6
                    : 1,
              }}
            >
              {lockoutRemainingSeconds > 0
                ? `Resend locked (${formatDuration(lockoutRemainingSeconds)})`
                : otpRemainingSeconds > 0
                  ? `Resend OTP in ${formatDuration(otpRemainingSeconds)}`
                  : 'Resend OTP'}
            </button>
          </div>
          <button
            type="submit"
            disabled={isSubmitting || otpExpired || !hasSubmittedContact}
            className={styles.primaryBtn}
          >
            {isSubmitting ? 'Submitting...' : 'Verify OTP'}
          </button>
        </form>
      )}
    </div>
  );
}
