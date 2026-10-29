import React, { useState, useRef } from 'react';
import { 
  Send, Paperclip, Globe, Mic, MicOff, X, Loader2, FileText, Image as ImageIcon, Music, Square
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

  const fileInputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

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
  };

  const processFiles = async (files) => {
    if (!files || files.length === 0) return;
    setIsUploading(true);
    try {
      for (const file of files) {
        const uploaded = await api.uploadAttachment(file);
        setAttachments((prev) => [...prev, uploaded]);
      }
    } catch (err) {
      alert(`Attachment upload failed: ${err.message}`);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
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
    setAttachments((prev) => prev.filter((a) => a.id !== id));
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
            alert(`Voice transcription failed: ${err.message}`);
          } finally {
            setIsUploading(false);
            stream.getTracks().forEach((track) => track.stop());
          }
        };

        mediaRecorder.start();
        setIsRecording(true);
      } catch (err) {
        alert(`Microphone access error: ${err.message}`);
      }
    }
  };

  const applyPromptChip = (chip) => {
    setText((prev) => (prev ? `${prev} ${chip.prompt}` : chip.prompt));
    if (chip.label.includes('PDF') && attachments.length === 0) {
      setTimeout(() => {
        fileInputRef.current?.click();
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
            <span>Uploading & parsing document...</span>
          </div>
        )}

        {/* Attachment preview pills */}
        {attachments.length > 0 && (
          <div className="composer-attachments-bar">
            {attachments.map((att) => (
              <div key={att.id} className="composer-attachment-tag">
                {att.attachment_type === 'image' && <ImageIcon size={12} />}
                {att.attachment_type === 'document' && <FileText size={12} />}
                {att.attachment_type === 'audio' && <Music size={12} />}
                <span>{att.file_name}</span>
                <button 
                  className="remove-tag-btn" 
                  onClick={() => removeAttachment(att.id)}
                  title="Remove attachment"
                >
                  <X size={12} />
                </button>
              </div>
            ))}
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
            margin: '6px 8px 0 8px',
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
              onClick={() => fileInputRef.current?.click()}
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

        {/* Input Textarea */}
        <div className="composer-input-row">
          <textarea
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
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: 'none' }}
            multiple
            accept=".png,.jpg,.jpeg,.webp,.pdf,.docx,.txt,.md,.mp3,.wav,.m4a"
            onChange={handleFileChange}
          />

          {/* Attachment button */}
          <button
            className="composer-btn"
            title="Attach images, documents, or audio (or drag & drop)"
            disabled={isUploading}
            onClick={() => fileInputRef.current?.click()}
          >
            {isUploading ? <Loader2 size={16} className="animate-spin" /> : <Paperclip size={16} />}
          </button>

          {/* Microphone button */}
          <button
            className={`composer-btn mic-btn ${isRecording ? 'recording' : ''}`}
            title={isRecording ? 'Stop Recording' : 'Voice Input (Speech-to-Text)'}
            onClick={toggleRecording}
          >
            {isRecording ? <MicOff size={16} /> : <Mic size={16} />}
          </button>

          {/* Web Search toggle */}
          <button
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
