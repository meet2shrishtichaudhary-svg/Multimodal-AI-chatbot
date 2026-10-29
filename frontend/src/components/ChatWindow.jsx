import React, { useEffect, useRef } from 'react';
import { 
  Sparkles, Globe, Layers, Heart, FileText, Download, Trash2, Code, Compass, BarChart3
} from 'lucide-react';
import ChatMessage from './ChatMessage';
import MessageComposer from './MessageComposer';

const PERSONAS = [
  { id: 'general', label: 'Assistant', icon: <Sparkles size={13} /> },
  { id: 'code', label: 'Code Expert', icon: <Code size={13} /> },
  { id: 'creative', label: 'Creative', icon: <Compass size={13} /> },
  { id: 'analyst', label: 'Analyst', icon: <BarChart3 size={13} /> },
  { id: 'counselor', label: 'Support', icon: <Heart size={13} /> }
];

export default function ChatWindow({
  conversation,
  messages,
  isLoading,
  onStop,
  webSearchEnabled,
  onToggleWebSearch,
  onSendMessage,
  knowledgeDocsCount,
  onStarterClick,
  persona,
  onPersonaChange,
  onExportChat,
  onClearChat,
  onRegenerate
}) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const starters = [
    {
      title: 'Analyze Knowledge Base',
      desc: 'Ask questions about your uploaded PDFs, DOCXs, or notes with grounded citations.',
      prompt: 'Can you summarize the main findings from the uploaded documents?',
      icon: <Layers size={16} style={{ color: 'var(--accent-indigo-light)' }} />
    },
    {
      title: 'Live Web Search',
      desc: 'Get recent facts and verified source links on any live topic.',
      prompt: 'What are the most recent developments in artificial intelligence this week?',
      icon: <Globe size={16} style={{ color: 'var(--accent-cyan)' }} />
    },
    {
      title: 'Empathetic Companion',
      desc: 'A supportive, safe space to talk through stress and get gentle, practical ideas.',
      prompt: "I've been feeling overwhelmed and stressed lately and could use a supportive conversation.",
      icon: <Heart size={16} style={{ color: 'var(--accent-rose)' }} />
    },
    {
      title: 'Document Creator',
      desc: 'Draft structured reports, guides, or specifications in seconds.',
      prompt: 'Draft an executive project proposal for a new modern web application.',
      icon: <FileText size={16} style={{ color: 'var(--accent-emerald)' }} />
    }
  ];

  return (
    <div className="main-content">
      {/* Top Header Bar */}
      <div className="top-bar">
        <div className="top-title-area">
          <span className="top-title">{conversation?.title || 'New Conversation'}</span>
        </div>

        {/* Persona Mode Switcher */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          background: 'rgba(255, 255, 255, 0.04)',
          padding: '3px 4px',
          borderRadius: '8px',
          border: '1px solid rgba(255, 255, 255, 0.08)'
        }}>
          {PERSONAS.map((p) => {
            const isSelected = (persona || 'general') === p.id;
            return (
              <button
                key={p.id}
                onClick={() => onPersonaChange && onPersonaChange(p.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  background: isSelected ? 'var(--accent-indigo)' : 'transparent',
                  color: isSelected ? '#fff' : 'var(--text-muted)',
                  border: 'none',
                  fontSize: '0.74rem',
                  padding: '3px 8px',
                  borderRadius: '5px',
                  cursor: 'pointer',
                  fontWeight: isSelected ? 600 : 400,
                  transition: 'all 0.15s ease'
                }}
                title={`Switch to ${p.label} mode`}
              >
                {p.icon}
                <span>{p.label}</span>
              </button>
            );
          })}
        </div>

        <div className="status-pills">
          {/* Action buttons: Export & Clear */}
          {conversation && (
            <>
              <button
                onClick={() => onExportChat && onExportChat('markdown')}
                className="status-pill"
                style={{ background: 'rgba(255, 255, 255, 0.06)', cursor: 'pointer', border: 'none' }}
                title="Export conversation as Markdown"
              >
                <Download size={11} />
                <span>Export .md</span>
              </button>
              <button
                onClick={() => onExportChat && onExportChat('json')}
                className="status-pill"
                style={{ background: 'rgba(255, 255, 255, 0.06)', cursor: 'pointer', border: 'none' }}
                title="Export conversation as JSON"
              >
                <Download size={11} />
                <span>JSON</span>
              </button>
              <button
                onClick={onClearChat}
                className="status-pill"
                style={{ background: 'rgba(244, 63, 94, 0.1)', color: 'var(--accent-rose)', cursor: 'pointer', border: 'none' }}
                title="Clear current messages"
              >
                <Trash2 size={11} />
                <span>Clear</span>
              </button>
            </>
          )}

          {knowledgeDocsCount > 0 && (
            <div className="status-pill" style={{ background: 'rgba(99, 102, 241, 0.15)', color: 'var(--accent-indigo-light)' }}>
              <Layers size={11} />
              <span>{knowledgeDocsCount} Docs</span>
            </div>
          )}

          {webSearchEnabled && (
            <div className="status-pill search-active">
              <Globe size={11} />
              <span>Live Search</span>
            </div>
          )}
        </div>
      </div>

      {/* Message History / Welcome Screen */}
      <div className="chat-messages-container" ref={scrollRef}>
        <div className="chat-max-width">
          {messages.length === 0 ? (
            <div className="welcome-hero">
              <div className="welcome-badge">
                <Sparkles size={13} />
                <span>Multimodal AI Assistant & Workspace</span>
              </div>
              <h1 className="welcome-title">How can I assist you today?</h1>
              <p className="welcome-subtitle">
                Interact with text, images, speech, and documents. Grounded in your knowledge base with live web search and specialized AI personas.
              </p>

              <div className="starters-grid">
                {starters.map((item, idx) => (
                  <div
                    key={idx}
                    className="starter-card"
                    onClick={() => onStarterClick(item.prompt)}
                  >
                    <div className="starter-card-title">
                      {item.icon}
                      <span>{item.title}</span>
                    </div>
                    <p className="starter-card-desc">{item.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} onRegenerate={onRegenerate} />
            ))
          )}

          {/* Typing indicator */}
          {isLoading && messages[messages.length - 1]?.role !== 'assistant' && (
            <div className="message-row assistant">
              <div className="message-avatar assistant">
                <Sparkles size={16} />
              </div>
              <div className="message-bubble assistant typing-row">
                <div className="typing-dot" />
                <div className="typing-dot" />
                <div className="typing-dot" />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Composer Input Bar */}
      <MessageComposer
        onSendMessage={onSendMessage}
        isLoading={isLoading}
        onStop={onStop}
        webSearchEnabled={webSearchEnabled}
        onToggleWebSearch={onToggleWebSearch}
      />
    </div>
  );
}
