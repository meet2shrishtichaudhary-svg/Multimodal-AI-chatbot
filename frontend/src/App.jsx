import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import DocumentWorkspace from './components/DocumentWorkspace';
import AuthModal from './components/AuthModal';
import ProfileModal from './components/ProfileModal';
import { api, authStorage } from './services/api';
import { resetSessionId } from './utils/session';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'workspace'
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [activeConversation, setActiveConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [knowledgeDocs, setKnowledgeDocs] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const [persona, setPersona] = useState('general');

  // Authentication & Profile Modals state
  const [user, setUser] = useState(() => authStorage.getUser());
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState('login');
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);

  const abortControllerRef = useRef(null);

  // Sync fresh profile if user is logged in
  useEffect(() => {
    if (authStorage.getToken()) {
      api.getMe()
        .then((freshUser) => {
          setUser(freshUser);
          if (freshUser.preferred_persona) {
            setPersona(freshUser.preferred_persona);
          }
        })
        .catch(() => {
          // Token expired or invalid
          setUser(null);
        });
    }
  }, []);

  // Load initial data
  const refreshData = async () => {
    try {
      const [convList, docList] = await Promise.all([
        api.listConversations(),
        api.listKnowledgeDocs()
      ]);
      setConversations(convList);
      setKnowledgeDocs(docList);

      if (convList.length > 0) {
        loadConversation(convList[0].id);
      } else {
        handleNewChat();
      }
    } catch (err) {
      console.warn('Refresh data error:', err);
    }
  };

  // Listen for global auth state changes
  useEffect(() => {
    const handleAuthChange = (e) => {
      setUser(e.detail);
      refreshData();
    };
    window.addEventListener('mm_auth_changed', handleAuthChange);
    return () => window.removeEventListener('mm_auth_changed', handleAuthChange);
  }, []);

  useEffect(() => {
    refreshData();
  }, []);

  const loadConversation = async (id) => {
    try {
      setActiveConversationId(id);
      const detail = await api.getConversation(id);
      setActiveConversation(detail);
      setMessages(detail.messages || []);
    } catch (err) {
      console.error('Error loading conversation:', err);
    }
  };

  const handleNewChat = () => {
    setActiveConversationId(null);
    setActiveConversation(null);
    setMessages([]);
  };

  const handleDeleteConversation = async (id) => {
    try {
      await api.deleteConversation(id);
      const updated = conversations.filter((c) => c.id !== id);
      setConversations(updated);
      if (activeConversationId === id) {
        if (updated.length > 0) {
          loadConversation(updated[0].id);
        } else {
          handleNewChat();
        }
      }
    } catch (err) {
      alert(`Could not delete conversation: ${err.message}`);
    }
  };

  const handleClearAllConversations = async () => {
    if (!window.confirm('Are you sure you want to delete all chat history?')) return;
    try {
      await api.clearAllConversations();
      setConversations([]);
      handleNewChat();
    } catch (err) {
      alert(`Failed to clear chats: ${err.message}`);
    }
  };

  const handleUploadKnowledgeDoc = async (file) => {
    const uploaded = await api.uploadKnowledgeDoc(file);
    setKnowledgeDocs((prev) => [uploaded, ...prev]);
    return uploaded;
  };

  const handleDeleteKnowledgeDoc = async (id) => {
    try {
      await api.deleteKnowledgeDoc(id);
      setKnowledgeDocs((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      alert(`Could not delete document: ${err.message}`);
    }
  };

  const handleSendMessage = async ({ message, attachmentIds, attachments }) => {
    if (isLoading) return;
    setIsLoading(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    const tempUserId = 'usr_' + Date.now();
    const tempAsstId = 'asst_' + Date.now();

    // Optimistic user message with attachment previews
    const userMsgObj = {
      id: tempUserId,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
      attachments: attachments || []
    };

    // Optimistic assistant message (starts empty for streaming)
    const assistantMsgObj = {
      id: tempAsstId,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
      msg_metadata: { citations: [] }
    };

    setMessages((prev) => [...prev, userMsgObj, assistantMsgObj]);

    try {
      await api.streamMessage(
        {
          conversation_id: activeConversationId,
          message,
          enable_web_search: webSearchEnabled,
          attachment_ids: attachmentIds || [],
          persona
        },
        {
          signal: controller.signal,
          onMetadata: (meta) => {
            if (!activeConversationId && meta.conversation_id) {
              setActiveConversationId(meta.conversation_id);
              api.listConversations().then(setConversations).catch(console.error);
            }
            if (meta.citations && meta.citations.length > 0) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === tempAsstId
                    ? { ...m, msg_metadata: { ...m.msg_metadata, citations: meta.citations } }
                    : m
                )
              );
            }
          },
          onToken: (token) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAsstId
                  ? { ...m, content: m.content + token }
                  : m
              )
            );
          },
          onDone: (doneData) => {
            setIsLoading(false);
            if (doneData.assistant_message_id) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === tempAsstId
                    ? { ...m, id: doneData.assistant_message_id }
                    : m
                )
              );
            }
          },
          onError: (err) => {
            console.error('Stream error:', err);
            setIsLoading(false);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAsstId
                  ? { ...m, content: m.content || '*(Connection issue: please try sending your message again)*' }
                  : m
              )
            );
          }
        }
      );
    } catch (err) {
      alert(`Chat error: ${err.message}`);
      setIsLoading(false);
    }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsLoading(false);
    }
  };

  const handleRegenerate = (asstMsg) => {
    // Find previous user message
    const asstIndex = messages.findIndex((m) => m.id === asstMsg.id);
    if (asstIndex > 0) {
      const prevUserMsg = messages[asstIndex - 1];
      if (prevUserMsg && prevUserMsg.role === 'user') {
        // Remove current assistant message and re-send
        setMessages((prev) => prev.slice(0, asstIndex));
        handleSendMessage({ message: prevUserMsg.content, attachmentIds: [] });
      }
    }
  };

  const handleExportChat = (format) => {
    if (!activeConversationId) {
      alert('Start a conversation first before exporting.');
      return;
    }
    const url = api.getExportUrl(activeConversationId, format);
    window.open(url, '_blank');
  };

  const handleResetSession = () => {
    resetSessionId();
    setConversations([]);
    setActiveConversationId(null);
    setActiveConversation(null);
    setMessages([]);
    setKnowledgeDocs([]);
    api.listConversations().then(setConversations).catch(console.error);
    api.listKnowledgeDocs().then(setKnowledgeDocs).catch(console.error);
  };

  const handleLogout = async () => {
    await api.logout();
    setUser(null);
    handleNewChat();
    refreshData();
  };

  return (
    <div className="app-container">
      <Sidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={loadConversation}
        onNewChat={handleNewChat}
        onDeleteConversation={handleDeleteConversation}
        knowledgeDocs={knowledgeDocs}
        onUploadDoc={handleUploadKnowledgeDoc}
        onDeleteDoc={handleDeleteKnowledgeDoc}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onResetSession={handleResetSession}
        user={user}
        onOpenAuth={() => {
          setAuthModalMode('login');
          setIsAuthModalOpen(true);
        }}
        onOpenProfile={() => setIsProfileModalOpen(true)}
        onLogout={handleLogout}
      />

      {activeTab === 'chat' ? (
        <ChatWindow
          conversation={activeConversation}
          messages={messages}
          isLoading={isLoading}
          onStop={handleStop}
          webSearchEnabled={webSearchEnabled}
          onToggleWebSearch={() => setWebSearchEnabled(!webSearchEnabled)}
          onSendMessage={handleSendMessage}
          knowledgeDocsCount={knowledgeDocs.length}
          onStarterClick={(prompt) => handleSendMessage({ message: prompt, attachmentIds: [] })}
          persona={persona}
          onPersonaChange={setPersona}
          onExportChat={handleExportChat}
          onClearChat={handleClearAllConversations}
          onRegenerate={handleRegenerate}
        />
      ) : (
        <DocumentWorkspace />
      )}

      {/* Auth Modal for Sign Up / Login / Password Reset */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        initialMode={authModalMode}
        onAuthSuccess={(authUser) => {
          setUser(authUser);
          if (authUser.preferred_persona) {
            setPersona(authUser.preferred_persona);
          }
          refreshData();
        }}
      />

      {/* Personal Profile & Settings Modal */}
      <ProfileModal
        isOpen={isProfileModalOpen}
        onClose={() => setIsProfileModalOpen(false)}
        user={user}
        onUpdateUser={(updatedUser) => {
          setUser(updatedUser);
          if (updatedUser.preferred_persona) {
            setPersona(updatedUser.preferred_persona);
          }
        }}
        onLogout={handleLogout}
      />
    </div>
  );
}
