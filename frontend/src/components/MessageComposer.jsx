import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, Paperclip, Globe, Mic, MicOff, X, Loader2, FileText, 
  Image as ImageIcon, Music, Square, Plus, Layers, AlertCircle
} from 'lucide-react';
import { api } from '../services/api';

const QUICK_PROMPTS = [
  { label: '🎨 Generate Image', prompt: 'Generate an image of ' },
  { label: '📄 Read & Analyze PDF', prompt: 'Please read the attached document and provide a thorough summary and key takeaways.' },
  { label: '💡 Explain Code', prompt: 'Please explain how this code works step-by-step with complexity analysis:\n' },
  { label: '📝 Summarize', prompt: 'Please provide a clear executive summary of the key takeaways from:\n' },
  { label: '🐞 Debug & Fix', prompt: 'Can you analyze this code for bugs, edge cases, and provide an optimized fix?\n' },
  { label: '🔍 Fact Check', prompt: 'Can you verify the factual accuracy of this statement with current sources?\n' }
];

const MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024; // 25 MB limit

const SUPPORTED_EXTENSIONS = {
  image: ['.png', '.jpg', '.jpeg', '.webp', '.gif'],
  document: ['.pdf', '.docx', '.txt', '.md'],
  audio: ['.mp3', '.wav', '.m4a', '.webm', '.ogg']
};

const ALL_ALLOWED_EXTS = [
  ...SUPPORTED_EXTENSIONS.image,
  ...SUPPORTED_EXTENSIONS.document,
  ...SUPPORTED_EXTENSIONS.audio
];

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export default function MessageComposer({
  onSendMessage,
  isLoading,
  onStop,
  webSearchEnabled,
  onToggleWebSearch
}) {
  const [text, setText] = useState('');
  const [attachments, setAttachments] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const menuRef = useRef(null);
  const imageInputRef = useRef(null);
  const docInputRef = useRef(null);
  const multiInputRef = useRef(null);
  const textareaRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // Close attachment menu on outside click or Escape key
  useEffect(() => {
    if (!isMenuOpen) return;
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setIsMenuOpen(false);
      }
    };
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setIsMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isMenuOpen]);

  // Auto-dismiss error alert after 6 seconds
  useEffect(() => {
    if (!errorMessage) return;
    const timer = setTimeout(() => {
      setErrorMessage(null);
    }, 6000);
    return () => clearTimeout(timer);
  }, [errorMessage]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    const trimmed = text.trim();
    if ((!trimmed && attachments.length === 0) || isLoading) return;

    onSendMessage({
      message: trimmed || 'Please analyze the attached document(s) and summarize key findings.',
      attachmentIds: attachments.map((a) => a.id),
      attachments: attachments
    });

    setText('');
    setAttachments([]);
    setErrorMessage(null);
    setIsMenuOpen(false);
  };

  const handleMenuOptionClick = (type) => {
    setIsMenuOpen(false);
    setErrorMessage(null);
    if (type === 'image') {
      imageInputRef.current?.click();
    } else if (type === 'document') {
      docInputRef.current?.click();
    } else if (type === 'multiple') {
      multiInputRef.current?.click();
    }
  };

  const processFiles = async (files) => {
    if (!files || files.length === 0) return;
    setErrorMessage(null);

    const validFiles = [];
    for (const file of files) {
      const ext = '.' + (file.name.split('.').pop() || '').toLowerCase();

      // Validate file size (max 25MB)
      if (file.size > MAX_UPLOAD_SIZE_BYTES) {
        const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
        setErrorMessage(`File "${file.name}" exceeds the 25MB limit (${sizeMb}MB). Please select a smaller file.`);
        continue;
      }

      // Validate file extension
      if (!ALL_ALLOWED_EXTS.includes(ext)) {
        setErrorMessage(
          `"${file.name}" has an unsupported format (${ext || 'unknown'}). Supported formats: Images (PNG, JPG, WEBP, GIF), Documents (PDF, DOCX, TXT, MD), and Audio (MP3, WAV, M4A).`
        );
        continue;
      }

      validFiles.push(file);
    }

    if (validFiles.length === 0) {
      if (imageInputRef.current) imageInputRef.current.value = '';
      if (docInputRef.current) docInputRef.current.value = '';
      if (multiInputRef.current) multiInputRef.current.value = '';
      return;
    }

    setIsUploading(true);
    try {
      for (const file of validFiles) {
        const ext = '.' + (file.name.split('.').pop() || '').toLowerCase();
        let previewUrl = null;
        if (SUPPORTED_EXTENSIONS.image.includes(ext)) {
          try {
            previewUrl = URL.createObjectURL(file);
          } catch (e) {
            console.warn('Could not generate object URL for preview:', e);
          }
        }

        const uploaded = await api.uploadAttachment(file);
        // Attach previewUrl and server fallback URL for immediate visual rendering
        uploaded.previewUrl = previewUrl || (uploaded.file_path ? `http://localhost:8000/uploads/${uploaded.file_path.split(/[\\/]/).pop()}` : null);
        setAttachments((prev) => [...prev, uploaded]);
      }
    } catch (err) {
      setErrorMessage(`Upload failed: ${err.message || 'Server error while processing file.'}`);
    } finally {
      setIsUploading(false);
      if (imageInputRef.current) imageInputRef.current.value = '';
      if (docInputRef.current) docInputRef.current.value = '';
      if (multiInputRef.current) multiInputRef.current.value = '';
    }
  };

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files || []);
    processFiles(files);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = Array.from(e.dataTransfer.files || []);
    processFiles(files);
  };

  const removeAttachment = (id) => {
    setAttachments((prev) => {
      const target = prev.find((a) => a.id === id);
      if (target && target.previewUrl && target.previewUrl.startsWith('blob:')) {
        try {
          URL.revokeObjectURL(target.previewUrl);
        } catch (_err) {
          // ignore
        }
      }
      return prev.filter((a) => a.id !== id);
    });
  };

  // Audio Recording (Speech-to-Text)
  const toggleRecording = async () => {
    if (isRecording) {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      setIsRecording(false);
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunksRef.current = [];
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;

        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunksRef.current.push(e.data);
        };

        mediaRecorder.onstop = async () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          const audioFile = new File([audioBlob], 'voice_record.webm', { type: 'audio/webm' });

          setIsUploading(true);
          try {
            const result = await api.transcribeAudio(audioFile);
            if (result && result.text) {
              setText((prev) => (prev ? `${prev} ${result.text}` : result.text));
            }
          } catch (err) {
            setErrorMessage(`Voice transcription failed: ${err.message}`);
          } finally {
            setIsUploading(false);
            stream.getTracks().forEach((track) => track.stop());
          }
        };

        mediaRecorder.start();
        setIsRecording(true);
      } catch (err) {
        setErrorMessage(`Microphone access error: ${err.message}`);
      }
    }
  };

  const applyPromptChip = (chip) => {
    setText((prev) => (prev ? `${prev} ${chip.prompt}` : chip.prompt));
    if (chip.label.includes('PDF') && attachments.length === 0) {
      setTimeout(() => {
        docInputRef.current?.click();
      }, 150);
    }
  };

  const mentionsPdfWithoutAttachment =
    attachments.length === 0 &&
    /\b(?:pdf|document|file|doc|paper|contract|resume|report)\b/i.test(text) &&
    /\b(?:read|summarize|analyze|analysis|review|extract|check|explain|look\s+at)\b/i.test(text);

  return (
    <div className="composer-area">
      {/* Quick Prompt Chips */}
      <div style={{
        display: 'flex',
        gap: '6px',
        overflowX: 'auto',
        paddingBottom: '8px',
        scrollbarWidth: 'none'
      }}>
        {QUICK_PROMPTS.map((chip, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => applyPromptChip(chip)}
            style={{
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              color: 'var(--text-muted)',
              fontSize: '0.74rem',
              padding: '4px 10px',
              borderRadius: '12px',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = '#fff';
              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = 'var(--text-muted)';
              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
            }}
          >
            {chip.label}
          </button>
        ))}
      </div>

      <div 
        className={`composer-card ${isDragOver ? 'drag-over' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        style={{
          border: isDragOver ? '1px dashed var(--accent-indigo)' : undefined,
          background: isDragOver ? 'rgba(99, 102, 241, 0.05)' : undefined
        }}
      >
        {/* Error Notification Banner */}
        {errorMessage && (
          <div className="composer-error-banner" role="alert">
            <div className="composer-error-content">
              <AlertCircle size={15} className="error-icon" />
              <span>{errorMessage}</span>
            </div>
            <button 
              type="button"
              className="composer-error-dismiss" 
              onClick={() => setErrorMessage(null)} 
              title="Dismiss error"
            >
              <X size={14} />
            </button>
          </div>
        )}

        {/* Uploading indicator */}
        {isUploading && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 14px',
            background: 'rgba(99, 102, 241, 0.1)',
            borderBottom: '1px solid rgba(99, 102, 241, 0.2)',
            fontSize: '0.78rem',
            color: 'var(--accent-indigo-light)'
          }}>
            <Loader2 size={13} className="animate-spin" />
            <span>Uploading & processing files...</span>
          </div>
        )}

        {/* Selected Attachments Preview Bar */}
        {attachments.length > 0 && (
          <div className="composer-attachments-bar">
            {attachments.map((att) => {
              // 1. Image Preview Card
              if (att.attachment_type === 'image') {
                const src = att.previewUrl || (att.file_path ? `http://localhost:8000/uploads/${att.file_path.split(/[\\/]/).pop()}` : '');
                return (
                  <div key={att.id} className="composer-attachment-card composer-image-card" title={att.file_name}>
                    <div className="composer-img-thumb-wrap">
                      <img src={src} alt={att.file_name} className="composer-thumb-img" />
                    </div>
                    <div className="composer-att-info">
                      <span className="composer-att-name">{att.file_name}</span>
                      <span className="composer-att-size">Image • {formatBytes(att.file_size)}</span>
                    </div>
                    <button 
                      type="button"
                      className="composer-card-remove-btn" 
                      onClick={() => removeAttachment(att.id)}
                      title="Remove image"
                    >
                      <X size={12} />
                    </button>
                  </div>
                );
              }

              // 2. Document Preview Card
              if (att.attachment_type === 'document') {
                const isPdf = att.file_name.toLowerCase().endsWith('.pdf');
                const isDocx = att.file_name.toLowerCase().endsWith('.docx');
                const badgeText = isPdf ? 'PDF' : isDocx ? 'DOCX' : 'DOC';

                return (
                  <div key={att.id} className="composer-attachment-card composer-doc-card" title={att.file_name}>
                    <div className="composer-doc-icon-badge">
                      <FileText size={16} />
                    </div>
                    <div className="composer-att-info">
                      <span className="composer-att-name">{att.file_name}</span>
                      <span className="composer-att-size">{badgeText} • {formatBytes(att.file_size)}</span>
                    </div>
                    <button 
                      type="button"
                      className="composer-card-remove-btn" 
                      onClick={() => removeAttachment(att.id)}
                      title="Remove document"
                    >
                      <X size={12} />
                    </button>
                  </div>
                );
              }

              // 3. Audio / Other Preview Card
              return (
                <div key={att.id} className="composer-attachment-card composer-audio-card" title={att.file_name}>
                  <div className="composer-audio-icon-badge">
                    <Music size={16} />
                  </div>
                  <div className="composer-att-info">
                    <span className="composer-att-name">{att.file_name}</span>
                    <span className="composer-att-size">Audio • {formatBytes(att.file_size)}</span>
                  </div>
                  <button 
                    type="button"
                    className="composer-card-remove-btn" 
                    onClick={() => removeAttachment(att.id)}
                    title="Remove audio file"
                  >
                    <X size={12} />
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* Unattached document prompt warning & quick action */}
        {mentionsPdfWithoutAttachment && !isUploading && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '8px',
            padding: '6px 12px',
            margin: '4px 0',
            background: 'rgba(234, 179, 8, 0.12)',
            border: '1px solid rgba(234, 179, 8, 0.28)',
            borderRadius: '6px',
            fontSize: '0.76rem',
            color: '#facc15'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Paperclip size={13} />
              <span>You mentioned a document: attach your PDF first so Aura can analyze it!</span>
            </div>
            <button
              type="button"
              onClick={() => docInputRef.current?.click()}
              style={{
                background: '#eab308',
                color: '#000',
                border: 'none',
                borderRadius: '4px',
                padding: '3px 8px',
                fontWeight: 600,
                fontSize: '0.72rem',
                cursor: 'pointer',
                whiteSpace: 'nowrap'
              }}
            >
              Attach PDF
            </button>
          </div>
        )}

        {/* Main Input Row: Circular Plus (+) Icon and Textarea */}
        <div className="composer-input-row">
          {/* Circular Plus (+) Icon Container */}
          <div className="composer-plus-container" ref={menuRef}>
            <button
              type="button"
              className={`composer-plus-btn ${isMenuOpen ? 'open' : ''}`}
              onClick={() => setIsMenuOpen((prev) => !prev)}
              title="Attach files"
              aria-label="Attach files"
              aria-expanded={isMenuOpen}
              disabled={isUploading}
            >
              <Plus size={18} className="plus-icon" />
            </button>

            {/* Smooth Floating Tooltip (shown when menu is closed) */}
            {!isMenuOpen && (
              <span className="composer-plus-tooltip">Attach files</span>
            )}

            {/* Attachment Menu Popup */}
            {isMenuOpen && (
              <div className="attachment-menu-popup" role="menu" aria-label="Attachment options">
                <div className="attachment-menu-header">
                  <span>Attach Content</span>
                </div>

                {/* Option 1: Upload Image */}
                <button
                  type="button"
                  className="attachment-menu-item"
                  role="menuitem"
                  onClick={() => handleMenuOptionClick('image')}
                >
                  <div className="menu-item-icon-wrap image-badge">
                    <ImageIcon size={16} />
                  </div>
                  <div className="menu-item-text">
                    <span className="menu-item-title">Upload Image</span>
                    <span className="menu-item-desc">PNG, JPG, WEBP, GIF</span>
                  </div>
                </button>

                {/* Option 2: Upload Document (PDF, DOCX, TXT) */}
                <button
                  type="button"
                  className="attachment-menu-item"
                  role="menuitem"
                  onClick={() => handleMenuOptionClick('document')}
                >
                  <div className="menu-item-icon-wrap doc-badge">
                    <FileText size={16} />
                  </div>
                  <div className="menu-item-text">
                    <span className="menu-item-title">Upload Document</span>
                    <span className="menu-item-desc">PDF, DOCX, TXT, MD</span>
                  </div>
                </button>

                {/* Option 3: Upload Multiple Files */}
                <button
                  type="button"
                  className="attachment-menu-item"
                  role="menuitem"
                  onClick={() => handleMenuOptionClick('multiple')}
                >
                  <div className="menu-item-icon-wrap multi-badge">
                    <Layers size={16} />
                  </div>
                  <div className="menu-item-text">
                    <span className="menu-item-title">Upload Multiple Files</span>
                    <span className="menu-item-desc">Select multiple images & documents</span>
                  </div>
                </button>
              </div>
            )}
          </div>

          {/* Hidden File Inputs */}
          <input
            type="file"
            ref={imageInputRef}
            style={{ display: 'none' }}
            multiple
            accept="image/png,image/jpeg,image/webp,image/gif"
            onChange={handleFileChange}
          />
          <input
            type="file"
            ref={docInputRef}
            style={{ display: 'none' }}
            multiple
            accept=".pdf,.docx,.txt,.md"
            onChange={handleFileChange}
          />
          <input
            type="file"
            ref={multiInputRef}
            style={{ display: 'none' }}
            multiple
            accept="image/png,image/jpeg,image/webp,image/gif,.pdf,.docx,.txt,.md,.mp3,.wav,.m4a"
            onChange={handleFileChange}
          />

          {/* Message Input Textarea */}
          <textarea
            ref={textareaRef}
            className="composer-textarea"
            rows={1}
            placeholder={
              isDragOver 
                ? 'Drop files here to upload...' 
                : isRecording 
                ? 'Listening to your voice...' 
                : 'Ask a question, paste code, drop a document, or share your thoughts...'
            }
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>

        {/* Controls row */}
        <div className="composer-controls">
          {/* Quick paperclip attachment shortcut */}
          <button
            type="button"
            className="composer-btn"
            title="Attach files (or use + icon)"
            disabled={isUploading}
            onClick={() => multiInputRef.current?.click()}
          >
            {isUploading ? <Loader2 size={16} className="animate-spin" /> : <Paperclip size={16} />}
          </button>

          {/* Microphone button */}
          <button
            type="button"
            className={`composer-btn mic-btn ${isRecording ? 'recording' : ''}`}
            title={isRecording ? 'Stop Recording' : 'Voice Input (Speech-to-Text)'}
            onClick={toggleRecording}
          >
            {isRecording ? <MicOff size={16} /> : <Mic size={16} />}
          </button>

          {/* Web Search toggle */}
          <button
            type="button"
            className={`search-toggle-btn ${webSearchEnabled ? 'active' : ''}`}
            title="Toggle Live Web Search grounding"
            onClick={onToggleWebSearch}
          >
            <Globe size={14} />
            <span>Live Search {webSearchEnabled ? 'ON' : 'OFF'}</span>
          </button>

          {/* Stop Button (when streaming/loading) or Send Button */}
          {isLoading ? (
            <button
              type="button"
              onClick={onStop}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                background: 'rgba(239, 68, 68, 0.2)',
                border: '1px solid var(--accent-rose)',
                color: 'var(--accent-rose)',
                padding: '7px 12px',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '0.8rem',
                fontWeight: 500
              }}
              title="Stop response generation"
            >
              <Square size={13} fill="currentColor" />
              <span>Stop</span>
            </button>
          ) : (
            <button
              type="button"
              className="send-btn"
              disabled={(!text.trim() && attachments.length === 0) || isUploading}
              onClick={handleSubmit}
              title="Send Message"
            >
              <Send size={15} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
