import React, { useRef, useState } from 'react';
import { 
  MessageSquare, Plus, Trash2, FileText, Upload, Sparkles, 
  Layers, RefreshCw, Settings, LogIn, LogOut, Search 
} from 'lucide-react';

export default function Sidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
  knowledgeDocs,
  onUploadDoc,
  onDeleteDoc,
  activeTab,
  onTabChange,
  onResetSession,
  user,
  onOpenAuth,
  onOpenProfile,
  onLogout
}) {
  const fileInputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);
  const [chatFilter, setChatFilter] = useState('');

  const filteredConversations = conversations.filter((c) =>
    !chatFilter.trim() || (c.title || '').toLowerCase().includes(chatFilter.toLowerCase())
  );

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setIsUploading(true);
      await onUploadDoc(file);
    } catch (err) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div className="sidebar-header">
        <div className="logo-area">
          <div className="logo-icon">
            <Sparkles size={18} />
          </div>
          <span className="logo-title">Aura AI</span>
        </div>
      </div>

      {/* Navigation Switcher */}
      <div className="nav-tabs">
        <button 
          className={`nav-tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => onTabChange('chat')}
        >
          <MessageSquare size={15} />
          <span>Chat</span>
        </button>
        <button 
          className={`nav-tab-btn ${activeTab === 'workspace' ? 'active' : ''}`}
          onClick={() => onTabChange('workspace')}
        >
          <FileText size={15} />
          <span>Workspace</span>
        </button>
      </div>

      {/* Action Button */}
      {activeTab === 'chat' ? (
        <button className="new-chat-btn" onClick={onNewChat}>
          <Plus size={16} />
          <span>New Chat</span>
        </button>
      ) : null}

      {/* Scrollable Items */}
      <div className="sidebar-scroll">
        {/* Conversations Group */}
        {activeTab === 'chat' && (
          <div>
            <div style={{ padding: '0 4px 8px 4px', position: 'relative' }}>
              <input
                type="text"
                placeholder="Search chats..."
                value={chatFilter}
                onChange={(e) => setChatFilter(e.target.value)}
                style={{
                  width: '100%',
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '6px 8px 6px 26px',
                  color: 'var(--text-primary)',
                  fontSize: '0.78rem',
                  outline: 'none'
                }}
              />
              <Search size={12} style={{ position: 'absolute', left: '12px', top: '7px', color: 'var(--text-muted)' }} />
            </div>

            <div className="section-label">
              <span>Conversations</span>
              <span>{filteredConversations.length}</span>
            </div>

            <div className="item-list">
              {filteredConversations.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', padding: '8px' }}>
                  {chatFilter ? 'No matching chats found.' : 'No chats yet. Start a new conversation!'}
                </div>
              ) : (
                filteredConversations.map((conv) => (
                  <div
                    key={conv.id}
                    className={`conversation-item ${conv.id === activeConversationId ? 'active' : ''}`}
                    onClick={() => onSelectConversation(conv.id)}
                  >
                    <span className="item-title">{conv.title || 'Untitled Chat'}</span>
                    <button
                      className="item-delete-btn"
                      title="Delete chat"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm('Delete this conversation?')) {
                          onDeleteConversation(conv.id);
                        }
                      }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Knowledge Base (RAG) */}
        <div>
          <div className="section-label">
            <span>Knowledge Base (RAG)</span>
            <span>{knowledgeDocs.length}</span>
          </div>

          <div className="item-list">
            {knowledgeDocs.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.78rem', padding: '6px' }}>
                Upload PDF, DOCX, TXT to enable grounded RAG answering.
              </div>
            ) : (
              knowledgeDocs.map((doc) => (
                <div key={doc.id} className="kb-item">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
                    <Layers size={13} style={{ color: 'var(--accent-indigo-light)', flexShrink: 0 }} />
                    <span className="item-title" style={{ fontSize: '0.8rem' }}>{doc.title}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span className="kb-badge">{doc.total_chunks} chunks</span>
                    <button
                      className="item-delete-btn"
                      title="Delete document"
                      onClick={() => {
                        if (confirm(`Remove ${doc.title} from knowledge base?`)) {
                          onDeleteDoc(doc.id);
                        }
                      }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              ))
            )}

            {/* Hidden File Input */}
            <input 
              type="file" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              accept=".pdf,.docx,.txt,.md"
              onChange={handleFileUpload}
            />

            <button 
              className="upload-kb-btn" 
              disabled={isUploading}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload size={14} />
              <span>{isUploading ? 'Chunking & Embedding...' : 'Upload Knowledge Doc'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* User Account / Guest Mode Footer */}
      <div style={{ padding: '12px 14px', borderTop: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.15)' }}>
        {user ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
            <div 
              onClick={onOpenProfile}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                flex: 1,
                minWidth: 0,
                cursor: 'pointer',
                padding: '4px 6px',
                borderRadius: 'var(--radius-sm)',
                transition: 'background 0.15s ease'
              }}
              className="user-profile-btn"
              title="View & edit personal profile"
            >
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #6366f1, #a855f7)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontWeight: 700,
                fontSize: '0.8rem',
                flexShrink: 0
              }}>
                {(user.full_name || user.email || 'U')[0].toUpperCase()}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {user.full_name || user.email.split('@')[0]}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--accent-indigo-light)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  Personal Profile
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
              <button
                onClick={onOpenProfile}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: '6px',
                  borderRadius: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
                title="Settings & Profile"
              >
                <Settings size={15} />
              </button>
              {onLogout && (
                <button
                  onClick={onLogout}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    padding: '6px',
                    borderRadius: '6px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                  title="Sign Out"
                >
                  <LogOut size={14} />
                </button>
              )}
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{
                  display: 'inline-block',
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: '#64748b'
                }} />
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Guest Mode</span>
              </div>
              <button 
                onClick={() => {
                  if (confirm('Start a fresh guest session? Current temporary local session will be renewed.')) {
                    onResetSession();
                  }
                }}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem' }}
                title="Renew anonymous session ID"
              >
                <RefreshCw size={11} />
                <span>Reset</span>
              </button>
            </div>

            <button
              onClick={onOpenAuth}
              style={{
                width: '100%',
                padding: '7px 10px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid rgba(99, 102, 241, 0.4)',
                background: 'rgba(99, 102, 241, 0.12)',
                color: 'var(--text-primary)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                fontSize: '0.8rem',
                fontWeight: 600,
                transition: 'all 0.15s ease'
              }}
              title="Sign in or register to sync your chats across sessions"
            >
              <LogIn size={13} style={{ color: 'var(--accent-indigo-light)' }} />
              <span>Sign In / Register</span>
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
