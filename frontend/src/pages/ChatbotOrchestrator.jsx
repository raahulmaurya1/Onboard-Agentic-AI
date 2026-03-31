import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ProgressStepper from '../components/ProgressStepper';
import AdditionalInfoFormView from './AdditionalInfoFormView';
import ChatView from './ChatView';
import DataReviewForm from './DataReviewForm';
import DecisionView from './DecisionView';
import EmailAuthView from './EmailAuthView';
import FaceVerificationView from './FaceVerificationView';
import FinalDashboardView from './FinalDashboardView';
import FinalReviewView from './FinalReviewView';
import KycUploadView from './KycUploadView';
import LifecycleSuccessView from './LifecycleSuccessView';
import PhoneAuthView from './PhoneAuthView';
import ProcessingView from './ProcessingView';
import { fetchReviewStatus, sendChatMessage, uploadDocuments } from './orchestratorApi';
import styles from './ChatbotOrchestrator.module.css';

const SUPPORTED_ACTIONS = new Set([
  'RENDER_CHAT',
  'RENDER_PHONE_AUTH',
  'RENDER_EMAIL_AUTH',
  'RENDER_KYC_UPLOAD',
  'RENDER_FACE_VERIFICATION',
  'RENDER_ADDITIONAL_INFO',
  'RENDER_ADDITIONAL_INFO_FORM',
  'RENDER_PROCESSING',
  'RENDER_DATA_REVIEW',
  'RENDER_FINAL_REVIEW',
  'RENDER_SUCCESS',
  'RENDER_AUTO_APPROVE',
  'RENDER_HUMAN_REVIEW',
  'RENDER_FINAL_DASHBOARD',
]);

const USER_ACTION_SOURCES = new Set([
  'chat_send',
  'phone_send_otp',
  'phone_verify_otp',
  'email_send_otp',
  'email_verify_otp',
  'kyc_upload_success_hook',
  'face_verification_success_hook',
  'submit_additional_info',
  'additional_info_submit',
  'final_review_submit',
  'data_review_confirm',
]);

const SESSION_STORAGE_KEY = 'onboardai_session_ulid';
const REVIEW_POLL_INTERVAL_MS = 3000;
const REVIEW_TIMEOUT_MS = 45000;
const EXTRACTION_TIMEOUT_TOAST =
  'Extraction timed out. Please try uploading clearer photos of your documents.';
const SESSION_IDENTITY_KEYS = ['phone', 'email', 'contact'];
const INITIAL_AGENT_GREETING =
  'Hello! I am your Onboard AI Agent.It is wonderful to meet you! Please feel free to ask any questions to begin your onboarding journey.';

function createUiMessage(role, text) {
  return {
    id: `${role}_${Date.now()}_${Math.random().toString(16).slice(2)}`,
    role,
    text,
    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  };
}

function extractIdentityFields(payload) {
  if (!payload || typeof payload !== 'object') return {};

  return SESSION_IDENTITY_KEYS.reduce((accumulator, key) => {
    const value = payload[key];
    if (typeof value === 'string') {
      const trimmed = value.trim();
      if (trimmed) {
        accumulator[key] = trimmed;
      }
    }
    return accumulator;
  }, {});
}

function mergeIdentityFields(previousState, payload) {
  const nextIdentity = extractIdentityFields(payload);
  if (!Object.keys(nextIdentity).length) {
    return previousState;
  }
  return {
    ...previousState,
    ...nextIdentity,
  };
}

export default function ChatbotOrchestrator({ onBack }) {
  const [currentAction, setCurrentAction] = useState('RENDER_CHAT');
  const [sessionUlid, setSessionUlid] = useState(null);
  const [messages, setMessages] = useState([
    createUiMessage('agent', INITIAL_AGENT_GREETING),
  ]);
  const [agentMessage, setAgentMessage] = useState('');
  const [dataRequired, setDataRequired] = useState([]);
  const [extractedData, setExtractedData] = useState(null);
  const [additionalInfoData, setAdditionalInfoData] = useState(null);
  const [sessionIdentity, setSessionIdentity] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [isAudioEnabled, setIsAudioEnabled] = useState(false);
  const [errorText, setErrorText] = useState('');
  const [toastText, setToastText] = useState('');
  const sessionUlidRef = useRef(sessionUlid);
  const sessionIdentityRef = useRef(sessionIdentity);
  const pollingIntervalRef = useRef(null);

  useEffect(() => {
    const storedSessionUlid = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (storedSessionUlid) {
      sessionUlidRef.current = storedSessionUlid;
      setSessionUlid(storedSessionUlid);
    }
  }, []);

  useEffect(() => {
    sessionUlidRef.current = sessionUlid;
    if (sessionUlid) {
      sessionStorage.setItem(SESSION_STORAGE_KEY, sessionUlid);
    } else {
      sessionStorage.removeItem(SESSION_STORAGE_KEY);
    }
  }, [sessionUlid]);

  useEffect(() => {
    sessionIdentityRef.current = sessionIdentity;
  }, [sessionIdentity]);

  useEffect(() => {
    if (!toastText) return undefined;
    const timeoutId = window.setTimeout(() => {
      setToastText('');
    }, 5000);
    return () => window.clearTimeout(timeoutId);
  }, [toastText]);

  useEffect(() => {
    const stopPolling = () => {
      if (pollingIntervalRef.current !== null) {
        window.clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };

    const normalizedCurrentAction = String(currentAction).trim().toUpperCase();
    if (normalizedCurrentAction !== 'RENDER_PROCESSING') {
      stopPolling();
      return undefined;
    }

    const activeSessionUlid =
      typeof sessionUlid === 'string' && sessionUlid.trim()
        ? sessionUlid.trim()
        : typeof sessionUlidRef.current === 'string' && sessionUlidRef.current.trim()
          ? sessionUlidRef.current.trim()
          : '';
    if (!activeSessionUlid) {
      return undefined;
    }

    let stopped = false;
    let pollInFlight = false;
    const startTs = Date.now();

    const finishWithTimeout = () => {
      if (stopped) return;
      stopped = true;
      stopPolling();
      setCurrentAction('RENDER_KYC_UPLOAD');
      setToastText(EXTRACTION_TIMEOUT_TOAST);
    };

    const pollStatus = async () => {
      if (stopped || pollInFlight) return;
      if (Date.now() - startTs >= REVIEW_TIMEOUT_MS) {
        finishWithTimeout();
        return;
      }

      pollInFlight = true;
      try {
        const reviewPayload = await fetchReviewStatus(activeSessionUlid);
        if (stopped) return;

        const nextUiActionRaw = typeof reviewPayload?.ui_action === 'string'
          ? reviewPayload.ui_action
          : typeof reviewPayload?.current_action === 'string'
            ? reviewPayload.current_action
            : '';
        const nextUiAction = nextUiActionRaw.trim().toUpperCase();
        const extractedDataPayload =
          reviewPayload?.extracted_data && typeof reviewPayload.extracted_data === 'object'
            ? reviewPayload.extracted_data
            : null;
        setSessionIdentity((previousState) => mergeIdentityFields(previousState, reviewPayload?.current_state));
        if (nextUiAction !== 'RENDER_DATA_REVIEW' || !extractedDataPayload) return;

        const combinedData = extractedDataPayload?.validation?.combined_data
          ?? extractedDataPayload?.combined_data;
        const gstData = extractedDataPayload?.gst_data
          ?? extractedDataPayload?.validation?.gst_data;
        setExtractedData(
          combinedData && typeof combinedData === 'object'
            ? {
                ...combinedData,
                ...(gstData && typeof gstData === 'object' ? { gst_data: gstData } : {}),
              }
            : extractedDataPayload
        );
        setAgentMessage(
          reviewPayload?.agent_message
            || 'Please review and correct extracted KYC details before submission.'
        );
        setDataRequired(
          Array.isArray(reviewPayload?.data_required) ? reviewPayload.data_required : []
        );
        setCurrentAction('RENDER_DATA_REVIEW');

        stopped = true;
        stopPolling();
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        const isExpectedPending = /status:\s*(404|202|204)\b/i.test(message);
        if (!isExpectedPending) {
          console.warn('[OnboardAI][ReviewPoll] Pending or transient poll failure', {
            session_ulid: activeSessionUlid,
            error: message,
          });
        }
      } finally {
        pollInFlight = false;
      }
    };

    void pollStatus();
    if (String(currentAction).toUpperCase() === 'RENDER_PROCESSING') {
      console.log('[OnboardAI][ReviewPoll] Polling started...');
      pollingIntervalRef.current = window.setInterval(() => {
        void pollStatus();
      }, REVIEW_POLL_INTERVAL_MS);
    }

    return () => {
      stopped = true;
      stopPolling();
    };
  }, [currentAction, sessionUlid]);

  const submitToOrchestrator = useCallback(
    async (text, meta) => {
      const trimmed = text.trim();
      if (!trimmed || isSubmitting) return null;
      if (!meta || !USER_ACTION_SOURCES.has(meta.source)) return null;
      const activeSessionUlid = sessionUlidRef.current;

      setErrorText('');
      if (!meta.hidden) {
        setMessages((prev) => [...prev, createUiMessage('user', trimmed)]);
      }
      setIsSubmitting(true);

      try {
        const currentState = {
          ...sessionIdentityRef.current,
          source: meta.source,
          current_action: currentAction,
          data_required: dataRequired,
        };
        const normalizedContact =
          typeof meta.contact === 'string' ? meta.contact.trim() : '';
        const normalizedPhone =
          typeof meta.phone === 'string' ? meta.phone.trim() : '';
        const normalizedEmail =
          typeof meta.email === 'string' ? meta.email.trim() : '';
        const normalizedOtp =
          typeof meta.otp === 'string' ? meta.otp.trim() : '';

        if (normalizedContact) {
          currentState.contact = normalizedContact;
        }
        if (normalizedOtp) {
          currentState.otp = normalizedOtp;
        }

        const inferredMode = typeof meta.mode === 'string' && meta.mode.trim()
          ? meta.mode.trim().toLowerCase()
          : meta.source.startsWith('phone_')
            ? 'phone'
            : meta.source.startsWith('email_')
              ? 'email'
              : '';
        const resolvedPhone = normalizedPhone || (inferredMode === 'phone' ? normalizedContact : '');
        const resolvedEmail = normalizedEmail || (inferredMode === 'email' ? normalizedContact : '');

        if (resolvedPhone) {
          currentState.phone = resolvedPhone;
        }
        if (resolvedEmail) {
          currentState.email = resolvedEmail;
        }
        if (typeof meta.command === 'string' && meta.command.trim()) {
          currentState.system_command = meta.command.trim();
        }
        setSessionIdentity((previousState) => mergeIdentityFields(previousState, currentState));
        console.log('[OnboardAI][Submit]', {
          message: trimmed,
          source: meta.source,
          session_ulid: activeSessionUlid ?? null,
          current_state: currentState,
        });

        const submitStartTs = Date.now();

        const result = await sendChatMessage({
          userMessage: trimmed,
          sessionUlid: activeSessionUlid,
          currentState,
          finalData: meta.finalData ?? null,
        });

        const elapsed = Date.now() - submitStartTs;
        const thinkingTimeMs = 1800;
        if (elapsed < thinkingTimeMs) {
          await new Promise((resolve) => setTimeout(resolve, thinkingTimeMs - elapsed));
        }

        const nextSessionUlid =
          typeof result.session_ulid === 'string' ? result.session_ulid.trim() : '';
        if (nextSessionUlid) {
          console.log('[OnboardAI][Session] Updating session_ulid from backend response', {
            previous_session_ulid: activeSessionUlid ?? null,
            next_session_ulid: nextSessionUlid,
            ui_action: result.ui_action,
          });
          sessionUlidRef.current = nextSessionUlid;
          setSessionUlid(nextSessionUlid);
        }

        const resultActionRaw = typeof result.ui_action === 'string'
          ? result.ui_action
          : typeof result.current_action === 'string'
            ? result.current_action
            : '';
        const normalizedResultAction = resultActionRaw.trim().toUpperCase();
        const nextAction = SUPPORTED_ACTIONS.has(normalizedResultAction)
          ? normalizedResultAction
          : 'RENDER_CHAT';
        setAgentMessage(result.agent_message);
        setDataRequired(result.data_required);
        setSessionIdentity((previousState) => mergeIdentityFields(previousState, result.current_state));
        if (
          (meta.source === 'additional_info_submit' || meta.source === 'submit_additional_info')
          && meta.finalData
          && typeof meta.finalData === 'object'
        ) {
          setAdditionalInfoData(meta.finalData);
        }
        if (nextAction === 'RENDER_PROCESSING') {
          setExtractedData(null);
        } else {
          setExtractedData(result.extracted_data ?? null);
        }

        if (result.agent_message) {
          setMessages((prev) => [...prev, createUiMessage('agent', result.agent_message)]);
        }

        if (nextAction !== currentAction && currentState.current_action === 'RENDER_CHAT') {
          setIsSubmitting(true);
          setIsTransitioning(true);
          setCurrentAction(nextAction);
          setIsTransitioning(false);
        } else {
          setCurrentAction(nextAction);
        }
        
        return result;
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unknown network error';
        setErrorText(message);
        setCurrentAction('RENDER_CHAT');
        setAgentMessage('I could not reach the backend orchestrator. Please try again.');
        setMessages((prev) => [
          ...prev,
          createUiMessage('agent', 'I could not reach the backend orchestrator. Please try again.'),
        ]);
        return null;
      } finally {
        setIsSubmitting(false);
      }
    },
    [currentAction, dataRequired, isSubmitting]
  );

  const handleDocumentsUploaded = useCallback(
    async (files) => {
      const activeSessionUlid = sessionUlidRef.current;
      await uploadDocuments({
        files,
        sessionUlid: activeSessionUlid,
        authToken: activeSessionUlid,
      });
      await submitToOrchestrator('SYSTEM: DOCUMENTS_UPLOADED_SUCCESSFULLY', {
        source: 'kyc_upload_success_hook',
        hidden: true,
      });
    },
    [submitToOrchestrator]
  );

  const handleLifecycleDone = useCallback(() => {
    sessionUlidRef.current = null;
    sessionIdentityRef.current = {};
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem(SESSION_STORAGE_KEY);
    }
    setSessionUlid(null);
    setSessionIdentity({});
    setExtractedData(null);
    setAdditionalInfoData(null);
    setDataRequired([]);
    setAgentMessage('');
    setErrorText('');
    setToastText('');
    setIsSubmitting(false);
    setIsTransitioning(false);
    setCurrentAction('RENDER_CHAT');
    setMessages([createUiMessage('agent', INITIAL_AGENT_GREETING)]);
    if (typeof onBack === 'function') {
      onBack();
    }
  }, [onBack]);

  const dynamicView = useMemo(() => {
    switch (currentAction) {
      case 'RENDER_PHONE_AUTH':
        return (
          <PhoneAuthView
            agentMessage={agentMessage}
            dataRequired={dataRequired}
            extractedData={extractedData}
            sessionIdentity={sessionIdentity}
            isSubmitting={isSubmitting}
            onSubmit={submitToOrchestrator}
          />
        );
      case 'RENDER_EMAIL_AUTH':
        return (
          <EmailAuthView
            agentMessage={agentMessage}
            dataRequired={dataRequired}
            extractedData={extractedData}
            sessionIdentity={sessionIdentity}
            isSubmitting={isSubmitting}
            onSubmit={submitToOrchestrator}
          />
        );
      case 'RENDER_KYC_UPLOAD':
        return (
          <KycUploadView
            agentMessage={agentMessage}
            dataRequired={dataRequired}
            isSubmitting={isSubmitting}
            onUploadDocuments={handleDocumentsUploaded}
          />
        );
      case 'RENDER_FACE_VERIFICATION':
        return (
          <FaceVerificationView
            agentMessage={agentMessage}
            sessionUlid={sessionUlid}
            onVerificationSuccess={() =>
              submitToOrchestrator('SYSTEM: FACE_VERIFICATION_SUCCESSFUL', {
                source: 'face_verification_success_hook',
                hidden: true,
                command: 'FACE_VERIFICATION_SUCCESSFUL',
              })
            }
          />
        );
      case 'RENDER_ADDITIONAL_INFO':
      case 'RENDER_ADDITIONAL_INFO_FORM':
        return (
          <AdditionalInfoFormView
            agentMessage={agentMessage}
            dataRequired={dataRequired}
            extractedData={extractedData}
            isSubmitting={isSubmitting}
            onSubmit={submitToOrchestrator}
          />
        );
      case 'RENDER_PROCESSING':
        return <ProcessingView />;
      case 'RENDER_DATA_REVIEW':
        return (
          <DataReviewForm
            agentMessage={agentMessage}
            extractedData={extractedData}
            isSubmitting={isSubmitting}
            onConfirm={(finalData) =>
              submitToOrchestrator('USER_CONFIRMED_DATA', {
                source: 'data_review_confirm',
                hidden: true,
                finalData,
              })
            }
          />
        );
      case 'RENDER_FINAL_REVIEW':
        return (
          <FinalReviewView
            agentMessage={agentMessage}
            finalData={additionalInfoData}
            isSubmitting={isSubmitting}
            onSubmit={(editedFinalData) =>
              submitToOrchestrator('SYSTEM: SUBMIT_ADDITIONAL_INFO', {
                source: 'final_review_submit',
                hidden: true,
                command: 'SUBMIT_ADDITIONAL_INFO',
                finalData:
                  editedFinalData && typeof editedFinalData === 'object'
                    ? editedFinalData
                    : additionalInfoData,
              })
            }
          />
        );
      case 'RENDER_SUCCESS':
        return (
          <LifecycleSuccessView
            message={agentMessage}
            onDone={handleLifecycleDone}
          />
        );
      case 'RENDER_AUTO_APPROVE':
        return (
          <DecisionView
            title="Application Auto-Approved"
            description={agentMessage || 'Your application has been approved automatically.'}
            sessionUlid={sessionUlid}
          />
        );
      case 'RENDER_HUMAN_REVIEW':
        return (
          <DecisionView
            title="Pending Human Review"
            description={agentMessage || 'Your application has been sent for manual review.'}
            sessionUlid={sessionUlid}
          />
        );
      case 'RENDER_FINAL_DASHBOARD':
        return <FinalDashboardView agentMessage={agentMessage} sessionUlid={sessionUlid} />;
      case 'RENDER_CHAT':
      default:
        return (
          <ChatView
            messages={messages}
            isSubmitting={isSubmitting || isTransitioning}
            showThinking={isSubmitting && !isTransitioning}
            isAudioEnabled={isAudioEnabled}
            onSend={submitToOrchestrator}
          />
        );
    }
  }, [
    additionalInfoData,
    agentMessage,
    currentAction,
    dataRequired,
    extractedData,
    handleDocumentsUploaded,
    handleLifecycleDone,
    isSubmitting,
    isTransitioning,
    isAudioEnabled,
    messages,
    sessionIdentity,
    sessionUlid,
    submitToOrchestrator,
  ]);

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <header className={styles.header}>
          <div className={styles.brandWrap}>
            <button className={styles.backBtn} onClick={onBack} type="button" aria-label="Back to home">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M12.6 4.6L7.2 10l5.4 5.4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
            <div className={styles.brandName}>Onboard AI</div>
            <span className={styles.onlineState}>
              <span className={styles.onlineDot} />
              Online
            </span>
          </div>
          <button 
            className={`${styles.audioToggleBtn} ${isAudioEnabled ? styles.audioOn : ''}`}
            onClick={() => setIsAudioEnabled(!isAudioEnabled)}
            aria-label={isAudioEnabled ? "Mute audio" : "Enable audio"}
            title={isAudioEnabled ? "Mute audio" : "Enable audio"}
          >
            {isAudioEnabled ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                <line x1="23" y1="9" x2="17" y2="15"></line>
                <line x1="17" y1="9" x2="23" y2="15"></line>
              </svg>
            )}
          </button>
        </header>

        {errorText && <div className={styles.errorBanner}>{errorText}</div>}
        {toastText && <div className={styles.toastBanner}>{toastText}</div>}

        <main className={styles.content}>
          <div className={styles.contentLayout}>
            <ProgressStepper currentAction={currentAction} />
            <div key={currentAction} className={styles.viewTransition}>
              {dynamicView}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
