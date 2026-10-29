import { getOrCreateSessionId } from '../utils/session';

const API_BASE = import.meta.env.VITE_API_BASE || (window.location.port === '5173' ? '/api' : 'http://localhost:8000/api');

const TOKEN_KEY = 'mm_auth_token';
const USER_KEY = 'mm_auth_user';

export const authStorage = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  setToken: (token) => {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  },
  getUser: () => {
    try {
      const u = localStorage.getItem(USER_KEY);
      return u ? JSON.parse(u) : null;
    } catch {
      return null;
    }
  },
  setUser: (user) => {
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
    else localStorage.removeItem(USER_KEY);
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
};

async function request(endpoint, options = {}) {
  const sessionId = getOrCreateSessionId();
  const token = authStorage.getToken();

  const headers = {
    'X-Session-ID': sessionId,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {})
  };

  // If not FormData, default to application/json
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    let errorDetail = 'API request failed';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    }
    // If token invalid / expired (401), clear local auth state
    if (response.status === 401 && token) {
      authStorage.clear();
      window.dispatchEvent(new CustomEvent('mm_auth_changed', { detail: null }));
    }
    throw new Error(errorDetail);
  }

  // If status is 204 No Content
  if (response.status === 204) {
    return null;
  }

  // Return blob if response is audio or file
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('audio/') || contentType.includes('application/octet-stream')) {
    return response.blob();
  }

  return response.json();
}

export const api = {
  // Health
  getHealth: () => request('/health'),

  // Conversations
  listConversations: () => request('/conversations'),
  getConversation: (id) => request(`/conversations/${id}`),
  updateConversationTitle: (id, title) =>
    request(`/conversations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ title })
    }),
  deleteConversation: (id) =>
    request(`/conversations/${id}`, {
      method: 'DELETE'
    }),
  clearAllConversations: () =>
    request('/conversations', {
      method: 'DELETE'
    }),
  getExportUrl: (id, format = 'markdown') => {
    const sessionId = getOrCreateSessionId();
    return `${API_BASE}/conversations/${id}/export?format=${format}&x_session_id=${sessionId}`;
  },

  // Chat
  sendMessage: (payload) =>
    request('/chat', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),

  streamMessage: async (payload, { onMetadata, onToken, onDone, onError, signal }) => {
    const sessionId = getOrCreateSessionId();
    const token = authStorage.getToken();
    try {
      const headers = {
        'Content-Type': 'application/json',
        'X-Session-ID': sessionId
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
        signal
      });

      if (!response.ok) {
        let errText = 'Streaming request failed';
        try {
          const errData = await response.json();
          errText = errData.detail || errText;
        } catch {}
        throw new Error(errText);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const block of lines) {
          const line = block.trim();
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6);
            try {
              const eventData = JSON.parse(jsonStr);
              if (eventData.type === 'metadata' && onMetadata) {
                onMetadata(eventData);
              } else if (eventData.type === 'token' && onToken) {
                onToken(eventData.delta);
              } else if (eventData.type === 'done' && onDone) {
                onDone(eventData);
              }
            } catch (jsonErr) {
              console.warn('SSE parse error:', jsonErr, jsonStr);
            }
          }
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        if (onDone) onDone({ aborted: true });
      } else {
        if (onError) onError(err);
        else console.error('Streaming error:', err);
      }
    }
  },

  // Uploads
  uploadAttachment: (file, conversationId = null) => {
    const formData = new FormData();
    formData.append('file', file);
    if (conversationId) {
      formData.append('conversation_id', conversationId);
    }
    return request('/uploads', {
      method: 'POST',
      body: formData
    });
  },

  // Knowledge Base Documents (RAG)
  listKnowledgeDocs: () => request('/documents'),
  uploadKnowledgeDoc: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return request('/documents/upload', {
      method: 'POST',
      body: formData
    });
  },
  deleteKnowledgeDoc: (id) =>
    request(`/documents/${id}`, {
      method: 'DELETE'
    }),

  // Search
  searchWeb: (query, max_results = 5) =>
    request('/search', {
      method: 'POST',
      body: JSON.stringify({ query, max_results })
    }),

  // Document Workspace
  listWorkspaces: (search = '') => request(`/documents/workspace${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  getWorkspace: (id) => request(`/documents/workspace/${id}`),
  renameWorkspace: (id, title) =>
    request(`/documents/workspace/${id}?title=${encodeURIComponent(title)}`, {
      method: 'PATCH'
    }),
  createWorkspace: ({ title, prompt, initial_content }) =>
    request('/documents/workspace', {
      method: 'POST',
      body: JSON.stringify({ title, prompt, initial_content })
    }),
  editWorkspace: (id, { instruction, current_content }) =>
    request(`/documents/workspace/${id}/edit`, {
      method: 'POST',
      body: JSON.stringify({ instruction, current_content })
    }),
  restoreWorkspaceVersion: (id, versionNumber) =>
    request(`/documents/workspace/${id}/restore/${versionNumber}`, {
      method: 'POST'
    }),
  compareWorkspaceVersions: (id, fromVer, toVer) =>
    request(`/documents/workspace/${id}/diff?from_version=${fromVer}&to_version=${toVer}`),
  getDownloadUrl: (id, format = 'docx') => {
    const sessionId = getOrCreateSessionId();
    return `${API_BASE}/documents/workspace/${id}/download?format=${format}&x_session_id=${sessionId}`;
  },

  // Audio (STT & TTS)
  transcribeAudio: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return request('/audio/transcribe', {
      method: 'POST',
      body: formData
    });
  },
  synthesizeSpeech: (text, voice = 'alloy') =>
    request('/audio/speak', {
      method: 'POST',
      body: JSON.stringify({ text, voice })
    }),

  // AI Image Generation
  generateImage: (prompt, conversation_id = null) =>
    request('/image/generate', {
      method: 'POST',
      body: JSON.stringify({ prompt, conversation_id })
    }),

  // Authentication & Personal Profile
  register: async ({ email, password, full_name, claim_guest_session_id }) => {
    const data = await request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name, claim_guest_session_id })
    });
    if (data.access_token) {
      authStorage.setToken(data.access_token);
      authStorage.setUser(data.user);
      window.dispatchEvent(new CustomEvent('mm_auth_changed', { detail: data.user }));
    }
    return data;
  },

  login: async ({ email, password, claim_guest_session_id }) => {
    const data = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password, claim_guest_session_id })
    });
    if (data.access_token) {
      authStorage.setToken(data.access_token);
      authStorage.setUser(data.user);
      window.dispatchEvent(new CustomEvent('mm_auth_changed', { detail: data.user }));
    }
    return data;
  },

  logout: async () => {
    try {
      await request('/auth/logout', { method: 'POST' });
    } catch {}
    authStorage.clear();
    window.dispatchEvent(new CustomEvent('mm_auth_changed', { detail: null }));
  },

  getMe: async () => {
    const user = await request('/auth/me');
    authStorage.setUser(user);
    return user;
  },

  updateProfile: async (profileData) => {
    const user = await request('/auth/profile', {
      method: 'PATCH',
      body: JSON.stringify(profileData)
    });
    authStorage.setUser(user);
    window.dispatchEvent(new CustomEvent('mm_auth_changed', { detail: user }));
    return user;
  },

  changePassword: ({ old_password, new_password }) =>
    request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ old_password, new_password })
    }),

  forgotPassword: (email) =>
    request('/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email })
    }),

  resetPassword: ({ email, reset_token, new_password }) =>
    request('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ email, reset_token, new_password })
    }),

  deleteAccount: async () => {
    const res = await request('/auth/me', { method: 'DELETE' });
    authStorage.clear();
    window.dispatchEvent(new CustomEvent('mm_auth_changed', { detail: null }));
    return res;
  },

  // Smart Memory Management
  listMemories: (activeOnly = false) => request(`/memory?active_only=${activeOnly}`),
  createMemory: ({ fact, category = 'general' }) =>
    request('/memory', {
      method: 'POST',
      body: JSON.stringify({ fact, category })
    }),
  updateMemory: (id, data) =>
    request(`/memory/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    }),
  deleteMemory: (id) =>
    request(`/memory/${id}`, {
      method: 'DELETE'
    }),
  clearMemories: () =>
    request('/memory', {
      method: 'DELETE'
    }),

  // Message Feedback & AI Evaluation
  submitFeedback: ({ message_id, rating, category = 'accuracy', comment = null }) =>
    request('/feedback', {
      method: 'POST',
      body: JSON.stringify({ message_id, rating, category, comment })
    })
};
