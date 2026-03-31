import React, { useEffect, useRef, useState } from 'react';
import styles from './ChatbotOrchestrator.module.css';

function formatLabel(key) {
  const normalized = String(key).trim().toLowerCase();
  const specialLabels = {
    name: 'Name',
    pan_id: 'PAN',
    dob: 'DOB',
    aadhaar: 'Aadhaar',
    aadhaar_id: 'Aadhaar',
  };
  if (specialLabels[normalized]) return specialLabels[normalized];
  return String(key)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function normalizeLabel(label) {
  return label.toLowerCase().replace(/\s+/g, '_').replace(/[^\w]/g, '');
}

function formatExtractedData(extractedData) {
  if (!extractedData || typeof extractedData !== 'object') return '';
  return Object.entries(extractedData)
    .filter(([, value]) => value !== null && typeof value !== 'object')
    .map(([key, value]) => `${formatLabel(key)}: ${String(value ?? '').trim()}`)
    .join('\n');
}

function parseReviewTextToFinalData(text, extractedData) {
  const keyLookup = new Map();
  if (extractedData && typeof extractedData === 'object') {
    Object.keys(extractedData).forEach((key) => {
      keyLookup.set(normalizeLabel(key), key);
      keyLookup.set(normalizeLabel(formatLabel(key)), key);
    });
  }

  const finalData = {};
  text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .forEach((line) => {
      const separatorIndex = line.indexOf(':');
      if (separatorIndex < 0) return;

      const label = line.slice(0, separatorIndex).trim();
      const value = line.slice(separatorIndex + 1).trim();
      if (!label) return;

      const normalizedLabel = normalizeLabel(label);
      const fallbackKey = normalizedLabel.replace(/^_+|_+$/g, '');
      const key = keyLookup.get(normalizedLabel) || fallbackKey;
      if (!key) return;
      finalData[key] = value;
    });

  return finalData;
}

export default function ChatView({
  messages,
  isSubmitting,
  showThinking,
  isAudioEnabled,
  onSend,
  isDataReviewMode = false,
  extractedData = null,
}) {
  const [draft, setDraft] = useState('');
  const textareaRef = useRef(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, showThinking]);

  const [isRecording, setIsRecording] = useState(false);
  const recognitionRef = useRef(null);
  const lastSpokenMessageId = useRef(null);

  useEffect(() => {
    if (!isAudioEnabled) {
      window.speechSynthesis.cancel();
      return;
    }
    if (messages && messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.role === 'agent' && lastSpokenMessageId.current !== lastMessage.id) {
        lastSpokenMessageId.current = lastMessage.id;
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(lastMessage.text);
        utterance.rate = 1.05;
        window.speechSynthesis.speak(utterance);
      }
    }
  }, [messages, isAudioEnabled]);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => setIsRecording(true);
      
      recognition.onresult = (event) => {
        let currentTranscript = '';
        for (let i = 0; i < event.results.length; i++) {
          currentTranscript += event.results[i][0].transcript;
        }
        setDraft(currentTranscript);
      };
      
      recognition.onerror = (event) => {
        console.error('Speech recognition error', event.error);
        setIsRecording(false);
      };
      
      recognition.onend = () => setIsRecording(false);
      recognitionRef.current = recognition;
    }
  }, []);

  const toggleRecording = () => {
    if (!recognitionRef.current) {
      alert("Speech recognition isn't supported securely in this browser.");
      return;
    }
    if (isRecording) {
      recognitionRef.current.stop();
    } else {
      setDraft('');
      recognitionRef.current.start();
    }
  };

  useEffect(() => {
    if (!isDataReviewMode) return;
    setDraft(formatExtractedData(extractedData));
  }, [isDataReviewMode, extractedData]);

  useEffect(() => {
    if (!textareaRef.current) return;
    textareaRef.current.style.height = 'auto';
    textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, isDataReviewMode ? 240 : 100)}px`;
  }, [draft, isDataReviewMode]);

  const handleSend = () => {
    const text = draft.trim();
    if (!text) return;

    if (isRecording && recognitionRef.current) {
      recognitionRef.current.stop();
    }

    if (isDataReviewMode) {
      const finalData = parseReviewTextToFinalData(draft, extractedData);
      if (Object.keys(finalData).length === 0) return;
      onSend('USER_CONFIRMED_DATA', {
        source: 'data_review_confirm',
        hidden: true,
        finalData,
      });
    } else {
      onSend(text, { source: 'chat_send' });
    }

    setDraft('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (event) => {
    if (isDataReviewMode) return;
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  const handleInput = (event) => {
    setDraft(event.target.value);
    event.target.style.height = 'auto';
    event.target.style.height = `${Math.min(event.target.scrollHeight, isDataReviewMode ? 240 : 100)}px`;
  };

  return (
    <div className={styles.chatView}>
      <div className={`${styles.messages} chat-scroll`}>
        {messages.map((message) => (
          <div
            key={message.id}
            className={`${styles.msgRow} ${message.role === 'user' ? styles.msgRowUser : ''}`}
          >
            <div
              className={`${styles.bubble} ${
                message.role === 'user' ? styles.userBubble : styles.agentBubble
              }`}
            >
              {message.text}
            </div>
            <div className={styles.timeLabel}>{message.time}</div>
          </div>
        ))}
        {showThinking && (
          <div className={`${styles.msgRow}`}>
            <div className={`${styles.bubble} ${styles.agentBubble}`}>
              <div className={styles.thinkingDots}>
                <span className={styles.dot}></span>
                <span className={styles.dot}></span>
                <span className={styles.dot}></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className={styles.composer}>
        <textarea
          ref={textareaRef}
          className={styles.textarea}
          rows={isDataReviewMode ? 6 : 1}
          value={draft}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={isDataReviewMode ? 'Review and edit extracted fields before submitting...' : 'Type a message for the orchestrator...'}
          disabled={isSubmitting}
        />
        {!isDataReviewMode && (
          <button
            type="button"
            className={`${styles.micBtn} ${isRecording ? styles.recording : ''}`}
            onClick={toggleRecording}
            disabled={isSubmitting}
            aria-label={isRecording ? "Stop recording" : "Start recording"}
            title={isRecording ? "Stop recording" : "Start recording"}
          >
            {isRecording ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                <line x1="12" y1="19" x2="12" y2="23"></line>
                <line x1="8" y1="23" x2="16" y2="23"></line>
              </svg>
            )}
          </button>
        )}
        <button
          type="button"
          className={styles.primaryBtn}
          onClick={handleSend}
          disabled={isSubmitting || !draft.trim()}
        >
          {isSubmitting ? 'Sending...' : isDataReviewMode ? 'Confirm & Submit' : (
            <>
              Send
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
