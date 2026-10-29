/**
 * Manages anonymous session UUID in localStorage.
 * Ensures each browser session is isolated and cannot view conversations or documents
 * belonging to other users.
 */
const SESSION_STORAGE_KEY = 'mm_chat_session_id';

export function getOrCreateSessionId() {
  let sessionId = localStorage.getItem(SESSION_STORAGE_KEY);
  if (!sessionId) {
    sessionId = 'sess_' + crypto.randomUUID();
    localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  }
  return sessionId;
}

export function resetSessionId() {
  const newId = 'sess_' + crypto.randomUUID();
  localStorage.setItem(SESSION_STORAGE_KEY, newId);
  return newId;
}
