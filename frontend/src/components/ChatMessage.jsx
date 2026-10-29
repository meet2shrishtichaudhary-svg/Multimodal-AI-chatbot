import React, { useState } from 'react';
import { 
  Bot, User, Volume2, Copy, Check, ExternalLink, FileText, CornerDownRight, RotateCcw, Code2, Sparkles, Download,
  ThumbsUp, ThumbsDown
} from 'lucide-react';
import { api } from '../services/api';

function GeneratedImageCard({ src, alt }) {
  const resolvedSrc = src?.startsWith('/uploads/') 
    ? (window.location.port === '5173' ? src : `http://localhost:8000${src}`)
    : src;

  return (
    <div className="generated-visual-card" style={{
      margin: '14px 0',
      borderRadius: '12px',
      overflow: 'hidden',
      border: '1px solid rgba(255, 255, 255, 0.12)',
      background: 'rgba(15, 23, 42, 0.85)',
      boxShadow: '0 8px 24px rgba(0, 0, 0, 0.35)'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 14px',
        background: 'rgba(255, 255, 255, 0.04)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        fontSize: '0.8rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sparkles size={14} style={{ color: '#ec4899' }} />
          <span style={{ fontWeight: 600, color: '#f1f5f9' }}>AI Generated Visual</span>
          {alt && <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>• {alt}</span>}
        </div>
        <a
          href={resolvedSrc}
          target="_blank"
          rel="noopener noreferrer"
          download
          style={{
            color: '#38bdf8',
            textDecoration: 'none',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            fontSize: '0.75rem',
            padding: '3px 8px',
            borderRadius: '6px',
            background: 'rgba(56, 189, 248, 0.12)',
            transition: 'background 0.2s'
          }}
          title="Open or download high-resolution image"
        >
          <Download size={13} />
          <span>Save</span>
        </a>
      </div>
      <div style={{
        padding: '12px',
        display: 'flex',
        justifyContent: 'center',
        background: '#090d16',
        maxHeight: '480px',
        overflow: 'hidden'
      }}>
        <img
          src={resolvedSrc}
          alt={alt || 'AI Visual'}
          style={{
            maxWidth: '100%',
            maxHeight: '440px',
            borderRadius: '8px',
            objectFit: 'contain',
            boxShadow: '0 4px 16px rgba(0,0,0,0.4)'
          }}
          loading="lazy"
        />
      </div>
    </div>
  );
}

function CodeBlock({ code, language }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="code-block-wrapper" style={{
      margin: '12px 0',
      borderRadius: '8px',
      overflow: 'hidden',
      border: '1px solid rgba(255, 255, 255, 0.1)',
      background: '#0d1117'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '6px 12px',
        background: 'rgba(255, 255, 255, 0.05)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        fontSize: '0.78rem',
        color: 'var(--text-muted)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Code2 size={13} style={{ color: 'var(--accent-indigo-light)' }} />
          <span>{language || 'code'}</span>
        </div>
        <button
          onClick={handleCopy}
          style={{
            background: 'transparent',
            border: 'none',
            color: copied ? 'var(--accent-emerald)' : 'var(--text-muted)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '0.75rem',
            padding: '2px 6px',
            borderRadius: '4px'
          }}
          title="Copy code"
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
          <span>{copied ? 'Copied!' : 'Copy'}</span>
        </button>
      </div>
      <pre style={{
        margin: 0,
        padding: '12px',
        overflowX: 'auto',
        fontSize: '0.86rem',
        fontFamily: 'Consolas, Monaco, "Courier New", monospace',
        lineHeight: 1.5,
        color: '#e6edf3'
      }}>
        <code>{code}</code>
      </pre>
    </div>
  );
}

export default function ChatMessage({ message, onRegenerate }) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState(null);

  const handleRate = async (rating) => {
    if (!message.id || String(message.id).startsWith('asst_')) return;
    try {
      setFeedbackRating(rating);
      await api.submitFeedback({ message_id: message.id, rating });
    } catch (err) {
      console.warn('Feedback submission error:', err);
    }
  };

  const citations = message.msg_metadata?.citations || [];
  const attachments = message.attachments || [];

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSpeech = async () => {
    if (isPlaying) return;
    try {
      setIsPlaying(true);
      const audioBlob = await api.synthesizeSpeech(message.content);
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audio.onended = () => setIsPlaying(false);
      audio.onerror = () => setIsPlaying(false);
      await audio.play();
    } catch (err) {
      console.warn('TTS playback error, fallback to browser speech synthesis:', err);
      if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(message.content);
        utterance.onend = () => setIsPlaying(false);
        utterance.onerror = () => setIsPlaying(false);
        window.speechSynthesis.speak(utterance);
      } else {
        setIsPlaying(false);
      }
    }
  };

  const renderTable = (rows, key) => {
    if (rows.length < 2) return null;
    const headerCols = rows[0].split('|').map((c) => c.trim()).filter(Boolean);
    const bodyRows = rows.slice(2).map((r) => r.split('|').map((c) => c.trim()).filter(Boolean));

    return (
      <div key={key} style={{ overflowX: 'auto', margin: '12px 0' }}>
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: '0.85rem',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '6px'
        }}>
          <thead>
            <tr style={{ background: 'rgba(255, 255, 255, 0.06)' }}>
              {headerCols.map((col, idx) => (
                <th key={idx} style={{ padding: '8px 12px', textAlign: 'left', borderBottom: '1px solid rgba(255, 255, 255, 0.15)', color: '#fff' }}>
                  {formatInlineText(col)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {bodyRows.map((cols, rIdx) => (
              <tr key={rIdx} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                {cols.map((cell, cIdx) => (
                  <td key={cIdx} style={{ padding: '8px 12px', color: 'var(--text-secondary)' }}>
                    {formatInlineText(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const renderFormattedContent = (text) => {
    if (!text) return null;

    // Split by code blocks
    const parts = text.split(/(```[\s\S]*?```)/g);

    return parts.map((part, index) => {
      if (part.startsWith('```') && part.endsWith('```')) {
        const headerMatch = part.match(/^```([a-zA-Z0-9_-]*)\n/);
        const language = headerMatch ? headerMatch[1] : '';
        const codeContent = part.replace(/^```[a-zA-Z0-9_-]*\n/, '').replace(/\n```$/, '');
        return <CodeBlock key={index} code={codeContent} language={language} />;
      }

      // Check for markdown tables inside lines
      const lines = part.split('\n');
      const elements = [];
      let tableBuffer = [];
      let inTable = false;

      for (let lIdx = 0; lIdx < lines.length; lIdx++) {
        const line = lines[lIdx];
        const trimmed = line.trim();

        if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
          inTable = true;
          tableBuffer.push(trimmed);
          continue;
        } else if (inTable) {
          elements.push(renderTable(tableBuffer, `tbl_${index}_${lIdx}`));
          tableBuffer = [];
          inTable = false;
        }

        if (!trimmed) {
          elements.push(<div key={`sp_${lIdx}`} style={{ height: '8px' }} />);
          continue;
        }

        const imgLineMatch = trimmed.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
        if (imgLineMatch) {
          elements.push(
            <GeneratedImageCard
              key={`img_${lIdx}`}
              alt={imgLineMatch[1]}
              src={imgLineMatch[2]}
            />
          );
          continue;
        }

        if (trimmed.startsWith('### ')) {
          elements.push(<h3 key={lIdx} style={{ fontSize: '1.05rem', margin: '8px 0 4px', color: '#fff' }}>{trimmed.slice(4)}</h3>);
        } else if (trimmed.startsWith('## ')) {
          elements.push(<h2 key={lIdx} style={{ fontSize: '1.15rem', margin: '12px 0 6px', color: '#fff' }}>{trimmed.slice(3)}</h2>);
        } else if (trimmed.startsWith('# ')) {
          elements.push(<h1 key={lIdx} style={{ fontSize: '1.25rem', margin: '14px 0 8px', color: '#fff' }}>{trimmed.slice(2)}</h1>);
        } else if (trimmed.startsWith('> [!IMPORTANT]') || trimmed.startsWith('> [!WARNING]')) {
          elements.push(
            <div key={lIdx} style={{ borderLeft: '3px solid var(--accent-rose)', padding: '8px 12px', background: 'rgba(244, 63, 94, 0.1)', borderRadius: '4px', margin: '8px 0' }}>
              <strong>Safety Notice:</strong>
            </div>
          );
        } else if (trimmed.startsWith('> ')) {
          elements.push(
            <blockquote key={lIdx} style={{ borderLeft: '3px solid var(--accent-indigo)', padding: '6px 12px', background: 'rgba(99, 102, 241, 0.08)', borderRadius: '0 6px 6px 0', margin: '6px 0' }}>
              {formatInlineText(trimmed.slice(2))}
            </blockquote>
          );
        } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
          elements.push(
            <li key={lIdx} style={{ marginLeft: '16px', marginBottom: '3px' }}>
              {formatInlineText(trimmed.slice(2))}
            </li>
          );
        } else {
          elements.push(<p key={lIdx} style={{ margin: '3px 0' }}>{formatInlineText(line)}</p>);
        }
      }

      if (inTable && tableBuffer.length > 0) {
        elements.push(renderTable(tableBuffer, `tbl_${index}_final`));
      }

      return <div key={index}>{elements}</div>;
    });
  };

  const formatInlineText = (text) => {
    if (!text) return text;
    // Replace inline images, code, links, and bold
    const tokens = text.split(/(!\[[^\]]*\]\([^)]+\)|`[^`]+`|\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*)/g);

    return tokens.map((token, idx) => {
      const imgMatch = token.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
      if (imgMatch) {
        return (
          <GeneratedImageCard
            key={idx}
            alt={imgMatch[1]}
            src={imgMatch[2]}
          />
        );
      }
      if (token.startsWith('`') && token.endsWith('`')) {
        return (
          <code key={idx} style={{
            background: 'rgba(255, 255, 255, 0.1)',
            padding: '2px 5px',
            borderRadius: '4px',
            fontSize: '0.88em',
            fontFamily: 'monospace',
            color: 'var(--accent-cyan)'
          }}>
            {token.slice(1, -1)}
          </code>
        );
      }
      if (token.startsWith('**') && token.endsWith('**')) {
        return <strong key={idx} style={{ color: '#fff' }}>{token.slice(2, -2)}</strong>;
      }
      const linkMatch = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (linkMatch) {
        return (
          <a key={idx} href={linkMatch[2]} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-cyan)', textDecoration: 'underline' }}>
            {linkMatch[1]}
          </a>
        );
      }
      return token;
    });
  };

  return (
    <div className={`message-row ${isUser ? 'user' : 'assistant'}`}>
      <div className={`message-avatar ${isUser ? 'user' : 'assistant'}`}>
        {isUser ? <User size={18} /> : <Bot size={18} />}
      </div>

      <div className="message-bubble-wrapper">
        {attachments.length > 0 && (
          <div className="msg-attachments-strip">
            {attachments.map((att) => {
              if (att.attachment_type === 'image') {
                return (
                  <img
                    key={att.id}
                    src={att.file_path ? `http://localhost:8000/uploads/${att.file_path.split(/[\\/]/).pop()}` : ''}
                    alt={att.file_name}
                    className="msg-img-thumb"
                  />
                );
              }
              return (
                <div key={att.id} className="msg-doc-pill">
                  <FileText size={13} style={{ color: 'var(--accent-indigo-light)' }} />
                  <span>{att.file_name}</span>
                </div>
              );
            })}
          </div>
        )}

        <div className={`message-bubble ${isUser ? 'user' : 'assistant'}`}>
          {renderFormattedContent(message.content)}

          {citations.length > 0 && (
            <div className="citations-box">
              <div className="citations-header">
                <CornerDownRight size={12} />
                <span>Sources & Grounded Citations ({citations.length})</span>
              </div>
              <div className="citations-cards">
                {citations.map((cite, i) => (
                  <a
                    key={i}
                    href={cite.url || '#'}
                    target={cite.url ? '_blank' : '_self'}
                    rel="noopener noreferrer"
                    className="citation-card"
                    title={cite.snippet}
                  >
                    {cite.source_type === 'web' ? <ExternalLink size={12} /> : <FileText size={12} />}
                    <span>{cite.title || cite.document_title}</span>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="message-meta">
          <span>{message.created_at ? new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}</span>
          
          <button className="listen-btn" onClick={handleCopy} title="Copy message text">
            {copied ? <Check size={12} style={{ color: 'var(--accent-emerald)' }} /> : <Copy size={12} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>

          {!isUser && (
            <>
              <button className="listen-btn" onClick={handleSpeech} title="Read response aloud">
                <Volume2 size={12} style={{ color: isPlaying ? 'var(--accent-cyan)' : 'inherit' }} />
                <span>{isPlaying ? 'Speaking...' : 'Listen'}</span>
              </button>
              {onRegenerate && (
                <button className="listen-btn" onClick={() => onRegenerate(message)} title="Regenerate this response">
                  <RotateCcw size={12} />
                  <span>Regenerate</span>
                </button>
              )}
              <button
                className="listen-btn"
                onClick={() => handleRate(1)}
                style={{ color: feedbackRating === 1 ? '#34d399' : 'inherit' }}
                title="Helpful response"
              >
                <ThumbsUp size={12} />
              </button>
              <button
                className="listen-btn"
                onClick={() => handleRate(-1)}
                style={{ color: feedbackRating === -1 ? '#f87171' : 'inherit' }}
                title="Unhelpful response"
              >
                <ThumbsDown size={12} />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
