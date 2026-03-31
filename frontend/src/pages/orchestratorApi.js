const ORCHESTRATOR_ENDPOINT = 'http://127.0.0.1:8000/api/v1/orchestrator/chat';
const DOCUMENT_UPLOAD_ENDPOINT = 'http://127.0.0.1:8000/api/upload-documents';
const FACE_VERIFY_ENDPOINT = 'http://127.0.0.1:8000/api/v1/face/verify';
const FACE_STATUS_ENDPOINT_BASE = 'http://127.0.0.1:8000/api/v1/face/status';
const TOKEN_STORAGE_KEYS = [
  'onboardai_auth_token',
  'onboardai_access_token',
  'authToken',
  'accessToken',
  'access_token',
  'idToken',
  'id_token',
  'token',
  'jwt',
];
const TOKEN_VALUE_KEYS = ['access_token', 'accessToken', 'id_token', 'idToken', 'token', 'jwt'];

function readStorageValue(storage, key) {
  if (!storage || typeof storage.getItem !== 'function') return null;
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
}

function normalizeBearerToken(value) {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  return trimmed.replace(/^Bearer\s+/i, '').trim() || null;
}

function extractTokenFromObject(payload) {
  if (!payload || typeof payload !== 'object') return null;

  for (const key of TOKEN_VALUE_KEYS) {
    const value = payload[key];
    if (typeof value === 'string' && value.trim()) {
      return normalizeBearerToken(value);
    }
  }

  const nestedCandidates = [payload.auth, payload.user, payload.session, payload.tokens];
  for (const nested of nestedCandidates) {
    if (nested && typeof nested === 'object') {
      const nestedToken = extractTokenFromObject(nested);
      if (nestedToken) return nestedToken;
    }
  }

  return null;
}

function extractToken(rawValue) {
  if (typeof rawValue !== 'string') return null;
  const trimmed = rawValue.trim();
  if (!trimmed) return null;

  if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
    try {
      const parsed = JSON.parse(trimmed);
      const parsedToken = extractTokenFromObject(parsed);
      if (parsedToken) return parsedToken;
    } catch {
      // Ignore parse failures and treat as direct token below.
    }
  }

  return normalizeBearerToken(trimmed);
}

function getCurrentAuthToken() {
  if (typeof window === 'undefined') return null;

  const storages = [window.sessionStorage, window.localStorage];
  for (const storage of storages) {
    for (const key of TOKEN_STORAGE_KEYS) {
      const rawValue = readStorageValue(storage, key);
      const token = extractToken(rawValue);
      if (token) return token;
    }
  }

  return null;
}

export async function sendChatMessage({ userMessage, sessionUlid, currentState = {}, finalData = null }) {
  const requestPayload = {
    user_message: userMessage,
    session_ulid: sessionUlid ?? null,
    current_state: currentState,
  };
  if (finalData && typeof finalData === 'object') {
    requestPayload.final_data = finalData;
  }

  console.log('[OnboardAI][Orchestrator][Request]', requestPayload);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    controller.abort();
  }, 25000);

  let response;
  try {
    response = await fetch(ORCHESTRATOR_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestPayload),
      signal: controller.signal,
    });
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw new Error('Orchestrator request timed out after 25s.');
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Orchestrator request failed (${response.status}): ${errorBody || 'No response body'}`);
  }

  const payload = await response.json();
  console.log('[OnboardAI][Orchestrator][Response]', payload);

  return {
    ui_action: payload.ui_action || 'RENDER_CHAT',
    current_action: payload.current_action || payload.ui_action || 'RENDER_CHAT',
    agent_message: payload.agent_message || '',
    data_required: Array.isArray(payload.data_required) ? payload.data_required : [],
    session_ulid: payload.session_ulid ?? sessionUlid ?? null,
    current_state: payload.current_state && typeof payload.current_state === 'object'
      ? payload.current_state
      : null,
    extracted_data: payload.extracted_data && typeof payload.extracted_data === 'object'
      ? payload.extracted_data
      : null,
  };
}

export async function uploadDocuments({ files, sessionUlid, authToken = null }) {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });
  if (sessionUlid) {
    formData.append('session_ulid', sessionUlid);
  }

  const resolvedAuthToken =
    normalizeBearerToken(authToken)
    || normalizeBearerToken(sessionUlid)
    || getCurrentAuthToken();
  const headers = {};
  if (resolvedAuthToken) {
    headers.Authorization = `Bearer ${resolvedAuthToken}`;
  }

  console.log('[OnboardAI][Upload][Request]', {
    file_count: files.length,
    session_ulid: sessionUlid ?? null,
    has_auth_token: Boolean(resolvedAuthToken),
  });

  const response = await fetch(DOCUMENT_UPLOAD_ENDPOINT, {
    method: 'POST',
    headers: Object.keys(headers).length > 0 ? headers : undefined,
    body: formData,
    credentials: 'include',
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Document upload failed (${response.status}): ${errorBody || 'No response body'}`);
  }

  let payload = {};
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }

  console.log('[OnboardAI][Upload][Response]', payload);
  return payload;
}

export const fetchReviewStatus = async (sessionId) => {
  const normalizedSessionId = typeof sessionId === 'string' ? sessionId.trim() : '';
  if (!normalizedSessionId) {
    throw new Error('Extraction in progress... Status: 404');
  }

  try {
    const response = await fetch(`http://127.0.0.1:8000/api/v1/orchestrator/review/${encodeURIComponent(normalizedSessionId)}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    if (!response.ok) {
      // A 404 simply means Celery is still extracting the documents. Keep polling!
      throw new Error(`Extraction in progress... Status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    throw error;
  }
};

export async function submitFaceVerification({ sessionUlid, livePhoto, liveVideo, authToken = null }) {
  const normalizedSessionUlid = typeof sessionUlid === 'string' ? sessionUlid.trim() : '';
  if (!normalizedSessionUlid) {
    throw new Error('Face verification requires a valid session_ulid.');
  }
  if (!(livePhoto instanceof Blob)) {
    throw new Error('Face verification requires a live photo.');
  }
  if (!(liveVideo instanceof Blob)) {
    throw new Error('Face verification requires a live video.');
  }

  const formData = new FormData();
  formData.append('session_ulid', normalizedSessionUlid);
  formData.append('live_photo', livePhoto);
  formData.append('live_video', liveVideo);

  const resolvedAuthToken =
    normalizeBearerToken(authToken)
    || normalizeBearerToken(normalizedSessionUlid)
    || getCurrentAuthToken();
  const headers = {};
  if (resolvedAuthToken) {
    headers.Authorization = `Bearer ${resolvedAuthToken}`;
  }

  console.log('[OnboardAI][FaceVerify][Submit][Request]', {
    session_ulid: normalizedSessionUlid,
    live_photo_type: livePhoto.type || null,
    live_video_type: liveVideo.type || null,
    has_auth_token: Boolean(resolvedAuthToken),
  });

  const response = await fetch(FACE_VERIFY_ENDPOINT, {
    method: 'POST',
    headers: Object.keys(headers).length > 0 ? headers : undefined,
    body: formData,
    credentials: 'include',
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Face verification submit failed (${response.status}): ${errorBody || 'No response body'}`);
  }

  let payload = {};
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }

  console.log('[OnboardAI][FaceVerify][Submit][Response]', payload);
  return payload;
}

export async function fetchFaceVerificationStatus(sessionUlid) {
  const normalizedSessionUlid = typeof sessionUlid === 'string' ? sessionUlid.trim() : '';
  if (!normalizedSessionUlid) {
    throw new Error('Face verification polling requires a valid session_ulid.');
  }

  const response = await fetch(
    `${FACE_STATUS_ENDPOINT_BASE}/${encodeURIComponent(normalizedSessionUlid)}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
    }
  );

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Face verification status failed (${response.status}): ${errorBody || 'No response body'}`);
  }

  const payload = await response.json();
  console.log('[OnboardAI][FaceVerify][Status][Response]', payload);
  return payload;
}
