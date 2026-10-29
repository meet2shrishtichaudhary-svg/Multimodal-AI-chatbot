import React, { useState, useEffect } from 'react';
import { 
  FileText, Plus, Download, Sparkles, History, Loader2, RotateCcw, Search 
} from 'lucide-react';
import { api } from '../services/api';

export default function DocumentWorkspace() {
  const [workspaces, setWorkspaces] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeWorkspaceId, setActiveWorkspaceId] = useState(null);
  const [activeWorkspace, setActiveWorkspace] = useState(null);
  const [instruction, setInstruction] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // New doc form states
  const [newTitle, setNewTitle] = useState('');
  const [newPrompt, setNewPrompt] = useState('');

  const loadWorkspaces = async (query = '') => {
    try {
      const list = await api.listWorkspaces(query);
      setWorkspaces(list);
      if (list.length > 0 && !activeWorkspaceId) {
        loadWorkspaceDetail(list[0].id);
      }
    } catch (err) {
      console.error('Error loading workspaces:', err);
    }
  };

  // Load workspaces on mount or search
  useEffect(() => {
    loadWorkspaces(searchQuery);
  }, [searchQuery]);

  const loadWorkspaceDetail = async (id) => {
    try {
      setActiveWorkspaceId(id);
      const detail = await api.getWorkspace(id);
      setActiveWorkspace(detail);
    } catch (err) {
      alert(`Could not load document: ${err.message}`);
    }
  };

  const handleRestoreVersion = async (versionNumber) => {
    if (!window.confirm(`Restore document to revision v${versionNumber}?`)) return;
    try {
      setIsProcessing(true);
      await api.restoreWorkspaceVersion(activeWorkspaceId, versionNumber);
      await loadWorkspaceDetail(activeWorkspaceId);
      await loadWorkspaces(searchQuery);
    } catch (err) {
      alert(`Failed to restore version: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCreateNew = async (e) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    setIsProcessing(true);
    try {
      const created = await api.createWorkspace({
        title: newTitle,
        prompt: newPrompt || null
      });
      setShowCreateModal(false);
      setNewTitle('');
      setNewPrompt('');
      await loadWorkspaces();
      await loadWorkspaceDetail(created.id);
    } catch (err) {
      alert(`Document creation failed: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleApplyEdit = async () => {
    if (!instruction.trim() || !activeWorkspace) return;

    setIsProcessing(true);
    try {
      const latestContent = activeWorkspace.latest_version?.content || '';
      await api.editWorkspace(activeWorkspace.id, {
        instruction,
        current_content: latestContent
      });
      setInstruction('');
      await loadWorkspaceDetail(activeWorkspace.id);
    } catch (err) {
      alert(`Edit failed: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownload = (format) => {
    if (!activeWorkspace) return;
    const url = api.getDownloadUrl(activeWorkspace.id, format);
    window.open(url, '_blank');
  };

  const latestVersion = activeWorkspace?.latest_version;
  const previousVersion = activeWorkspace?.versions?.length > 1 ? activeWorkspace.versions[1] : null;

  return (
    <div className="workspace-container">
      {/* Top Action Bar */}
      <div className="workspace-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <FileText size={20} style={{ color: 'var(--accent-indigo-light)' }} />
          <span style={{ fontWeight: 700, fontSize: '1.05rem' }}>
            {activeWorkspace ? activeWorkspace.title : 'Document Workspace'}
          </span>
          {latestVersion && (
            <span style={{ fontSize: '0.75rem', background: 'rgba(99, 102, 241, 0.15)', color: 'var(--accent-indigo-light)', padding: '2px 8px', borderRadius: '12px' }}>
              v{latestVersion.version_number}
            </span>
          )}
        </div>

        <div className="workspace-actions">
          <button className="workspace-btn primary" onClick={() => setShowCreateModal(true)}>
            <Plus size={14} />
            <span>New Document</span>
          </button>

          {activeWorkspace && (
            <>
              <button className="workspace-btn" onClick={() => handleDownload('docx')} title="Download Word Document">
                <Download size={13} />
                <span>DOCX</span>
              </button>
              <button className="workspace-btn" onClick={() => handleDownload('md')} title="Download Markdown">
                <Download size={13} />
                <span>MD</span>
              </button>
              <button className="workspace-btn" onClick={() => handleDownload('txt')} title="Download Plain Text">
                <Download size={13} />
                <span>TXT</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Main Split Body */}
      <div className="workspace-split">
        {/* Left Documents & Version Navigation */}
        <div className="workspace-sidebar">
          <div>
            <div style={{ marginBottom: '8px', position: 'relative' }}>
              <input
                type="text"
                placeholder="Search documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="workspace-title-input"
                style={{ width: '100%', fontSize: '0.78rem', padding: '6px 8px 6px 26px' }}
              />
              <Search size={12} style={{ position: 'absolute', left: '8px', top: '9px', color: 'var(--text-muted)' }} />
            </div>

            <div className="section-label">
              <span>Your Documents</span>
              <span>{workspaces.length}</span>
            </div>
            <div className="item-list">
              {workspaces.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>No documents drafted yet.</div>
              ) : (
                workspaces.map((ws) => (
                  <div
                    key={ws.id}
                    className={`conversation-item ${ws.id === activeWorkspaceId ? 'active' : ''}`}
                    onClick={() => loadWorkspaceDetail(ws.id)}
                  >
                    <span className="item-title">{ws.title}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Version History */}
          {activeWorkspace?.versions && (
            <div style={{ marginTop: '16px' }}>
              <div className="section-label">
                <History size={12} />
                <span>Revision History ({activeWorkspace.versions.length})</span>
              </div>
              <div className="item-list">
                {activeWorkspace.versions.map((ver, idx) => (
                  <div
                    key={ver.id}
                    className="kb-item"
                    style={{ fontSize: '0.78rem', flexDirection: 'column', alignItems: 'flex-start', gap: '3px' }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                      <strong>v{ver.version_number}</strong>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {idx > 0 && (
                          <button
                            type="button"
                            onClick={() => handleRestoreVersion(ver.version_number)}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: 'var(--accent-indigo-light)',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '2px',
                              fontSize: '0.7rem'
                            }}
                            title="Restore this revision"
                          >
                            <RotateCcw size={10} /> Restore
                          </button>
                        )}
                        <span style={{ color: 'var(--text-muted)' }}>
                          {new Date(ver.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    </div>
                    <span style={{ color: 'var(--text-secondary)' }}>{ver.change_summary}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Center / Right Editor Panes */}
        <div className="workspace-main">
          {activeWorkspace ? (
            <>
              <div className="workspace-editor-area">
                {/* Previous Version for comparison if exists */}
                {previousVersion && (
                  <div className="editor-pane" style={{ opacity: 0.8 }}>
                    <div className="editor-pane-header">
                      <span>Previous Revision (v{previousVersion.version_number})</span>
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Read-only reference</span>
                    </div>
                    <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: '#94a3b8' }}>
                      {previousVersion.content}
                    </pre>
                  </div>
                )}

                {/* Current Active Revision */}
                <div className="editor-pane">
                  <div className="editor-pane-header">
                    <span>Current Revision (v{latestVersion?.version_number || 1})</span>
                    <span style={{ fontSize: '0.72rem', color: 'var(--accent-emerald)' }}>Active Draft</span>
                  </div>
                  <textarea
                    className="editor-textarea"
                    value={latestVersion?.content || ''}
                    readOnly
                    placeholder="Document content will appear here..."
                  />
                </div>
              </div>

              {/* AI Modification Instruction Bar */}
              <div className="workspace-edit-bar">
                <input
                  type="text"
                  className="workspace-instruction-input"
                  placeholder="Ask AI to edit this document (e.g. 'Add an executive summary', 'Translate to Spanish', 'Fix grammar')..."
                  value={instruction}
                  onChange={(e) => setInstruction(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleApplyEdit()}
                />
                <button
                  className="workspace-btn primary"
                  disabled={!instruction.trim() || isProcessing}
                  onClick={handleApplyEdit}
                >
                  {isProcessing ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                  <span>{isProcessing ? 'Rewriting...' : 'Apply AI Edit'}</span>
                </button>
              </div>
            </>
          ) : (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', gap: '12px' }}>
              <FileText size={40} style={{ opacity: 0.3 }} />
              <p>Select an existing document from the left or create a new one.</p>
              <button className="workspace-btn primary" onClick={() => setShowCreateModal(true)}>
                <Plus size={14} />
                <span>Create New Document</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Create New Document Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal-title">Create New Document</h3>
            <form onSubmit={handleCreateNew} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                  Document Title
                </label>
                <input
                  type="text"
                  required
                  className="workspace-instruction-input"
                  placeholder="e.g. Software Architecture Plan"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  style={{ width: '100%' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                  Drafting Prompt (Optional)
                </label>
                <textarea
                  className="workspace-instruction-input"
                  rows={4}
                  placeholder="Describe what you want the AI to draft (e.g. 'Draft a comprehensive project proposal for a healthcare mobile app including tech stack, timeline, and risk matrix')..."
                  value={newPrompt}
                  onChange={(e) => setNewPrompt(e.target.value)}
                  style={{ width: '100%', resize: 'vertical' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '10px' }}>
                <button
                  type="button"
                  className="workspace-btn"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="workspace-btn primary"
                  disabled={!newTitle.trim() || isProcessing}
                >
                  {isProcessing ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                  <span>{isProcessing ? 'Generating...' : 'Create Document'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
