import React, { useState, useEffect } from 'react';
import { 
  X, Shield, Sliders, LogOut, CheckCircle2, 
  AlertCircle, Save, Sparkles, Key, Clock,
  Brain, Trash2, Plus 
} from 'lucide-react';
import { api } from '../services/api';

const PERSONAS = [
  { id: 'general', label: 'General Assistant', desc: 'Balanced, clear, and comprehensive.' },
  { id: 'code', label: 'Code Expert', desc: 'Focuses on clean code, architecture, and syntax.' },
  { id: 'creative', label: 'Creative Writer', desc: 'Vivid, descriptive, and engaging storytelling.' },
  { id: 'analyst', label: 'Data Analyst', desc: 'Structured analysis, metrics, and bullet summaries.' },
  { id: 'support', label: 'Support Agent', desc: 'Patient, courteous, and step-by-step guidance.' }
];

export default function ProfileModal({ isOpen, onClose, user, onUpdateUser, onLogout }) {
  const [activeTab, setActiveTab] = useState('profile'); // 'profile' | 'security' | 'session'

  // Profile Form state
  const [fullName, setFullName] = useState('');
  const [bio, setBio] = useState('');
  const [preferredPersona, setPreferredPersona] = useState('general');
  const [customInstructions, setCustomInstructions] = useState('');

  // Password Form state
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Memory state
  const [memories, setMemories] = useState([]);
  const [newFact, setNewFact] = useState('');
  const [newCategory, setNewCategory] = useState('preference');

  // Status feedback
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const loadMemories = async () => {
    try {
      const res = await api.listMemories();
      setMemories(res.memories || []);
    } catch (err) {
      console.warn('Error loading memories:', err);
    }
  };

  useEffect(() => {
    if (activeTab === 'memory') {
      loadMemories();
    }
  }, [activeTab]);

  const handleAddMemory = async (e) => {
    e.preventDefault();
    if (!newFact.trim()) return;
    try {
      setLoading(true);
      await api.createMemory({ fact: newFact.trim(), category: newCategory });
      setNewFact('');
      await loadMemories();
      setSuccessMsg('Memory fact saved!');
      setTimeout(() => setSuccessMsg(''), 2500);
    } catch (err) {
      setError(err.message || 'Failed to save memory.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteMemory = async (id) => {
    try {
      await api.deleteMemory(id);
      setMemories((prev) => prev.filter((m) => m.id !== id));
    } catch (err) {
      setError(err.message || 'Failed to delete memory.');
    }
  };

  const handleClearAllMemories = async () => {
    if (!window.confirm('Forget all saved memory facts?')) return;
    try {
      await api.clearMemories();
      setMemories([]);
      setSuccessMsg('All memories forgotten.');
      setTimeout(() => setSuccessMsg(''), 2500);
    } catch (err) {
      setError(err.message || 'Failed to clear memories.');
    }
  };

  useEffect(() => {
    if (user) {
      setFullName(user.full_name || '');
      setBio(user.bio || '');
      setPreferredPersona(user.preferred_persona || 'general');
      setCustomInstructions(user.custom_instructions || '');
    }
  }, [user]);

  if (!isOpen || !user) return null;

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError('');
      setSuccessMsg('');
      const updated = await api.updateProfile({
        full_name: fullName,
        bio,
        preferred_persona: preferredPersona,
        custom_instructions: customInstructions
      });
      if (onUpdateUser) onUpdateUser(updated);
      setSuccessMsg('Profile and custom instructions updated successfully!');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to update profile.');
    } finally {
      setLoading(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (!oldPassword || !newPassword) {
      setError('Both current and new passwords are required.');
      return;
    }
    if (newPassword.length < 6) {
      setError('New password must be at least 6 characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match.');
      return;
    }

    try {
      setLoading(true);
      setError('');
      setSuccessMsg('');
      const res = await api.changePassword({
        old_password: oldPassword,
        new_password: newPassword
      });
      setSuccessMsg(res.message || 'Password changed successfully!');
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to change password.');
    } finally {
      setLoading(false);
    }
  };

  const initials = (user.full_name || user.email || 'U')
    .split(' ')
    .map((n) => n[0])
    .join('')
    .substring(0, 2)
    .toUpperCase();

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div 
        className="modal-card" 
        onClick={(e) => e.stopPropagation()} 
        style={{ maxWidth: '560px', position: 'relative', maxHeight: '90vh', overflowY: 'auto' }}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '16px',
            right: '16px',
            background: 'transparent',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer'
          }}
          title="Close"
        >
          <X size={18} />
        </button>

        {/* User Card Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '16px' }}>
          <div 
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #6366f1, #a855f7)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.1rem',
              fontWeight: 700,
              color: 'white',
              boxShadow: '0 4px 12px rgba(99, 102, 241, 0.35)'
            }}
          >
            {initials}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h3 style={{ margin: 0, fontSize: '1.15rem', color: 'var(--text-primary)', fontWeight: 600 }}>
                {user.full_name || 'Personal Account'}
              </h3>
              <span style={{
                background: 'rgba(99, 102, 241, 0.15)',
                color: 'var(--accent-indigo-light)',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                padding: '2px 8px',
                borderRadius: '12px',
                fontSize: '0.7rem',
                fontWeight: 600
              }}>
                Pro Member
              </span>
            </div>
            <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {user.email}
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div style={{
          display: 'flex',
          background: 'rgba(255, 255, 255, 0.04)',
          borderRadius: 'var(--radius-sm)',
          padding: '4px',
          gap: '4px'
        }}>
          <button
            type="button"
            onClick={() => { setActiveTab('profile'); setError(''); setSuccessMsg(''); }}
            style={{
              flex: 1,
              padding: '8px 10px',
              borderRadius: '6px',
              border: 'none',
              background: activeTab === 'profile' ? 'var(--accent-indigo)' : 'transparent',
              color: activeTab === 'profile' ? '#fff' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.82rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px'
            }}
          >
            <Sliders size={14} /> Profile & Preferences
          </button>
          <button
            type="button"
            onClick={() => { setActiveTab('memory'); setError(''); setSuccessMsg(''); }}
            style={{
              flex: 1,
              padding: '8px 10px',
              borderRadius: '6px',
              border: 'none',
              background: activeTab === 'memory' ? 'var(--accent-indigo)' : 'transparent',
              color: activeTab === 'memory' ? '#fff' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.82rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px'
            }}
          >
            <Brain size={14} /> AI Memory
          </button>
          <button
            type="button"
            onClick={() => { setActiveTab('security'); setError(''); setSuccessMsg(''); }}
            style={{
              flex: 1,
              padding: '8px 10px',
              borderRadius: '6px',
              border: 'none',
              background: activeTab === 'security' ? 'var(--accent-indigo)' : 'transparent',
              color: activeTab === 'security' ? '#fff' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.82rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px'
            }}
          >
            <Shield size={14} /> Security
          </button>
          <button
            type="button"
            onClick={() => { setActiveTab('session'); setError(''); setSuccessMsg(''); }}
            style={{
              flex: 1,
              padding: '8px 10px',
              borderRadius: '6px',
              border: 'none',
              background: activeTab === 'session' ? 'var(--accent-indigo)' : 'transparent',
              color: activeTab === 'session' ? '#fff' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.82rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px'
            }}
          >
            <Clock size={14} /> Session
          </button>
        </div>

        {/* Feedback Banners */}
        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            borderRadius: 'var(--radius-sm)',
            padding: '10px 12px',
            color: '#fca5a5',
            fontSize: '0.82rem',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '8px'
          }}>
            <AlertCircle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div style={{
            background: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.4)',
            borderRadius: 'var(--radius-sm)',
            padding: '10px 12px',
            color: '#6ee7b7',
            fontSize: '0.82rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
            <span>{successMsg}</span>
          </div>
        )}

        {/* TAB 1: PROFILE & PREFERENCES */}
        {activeTab === 'profile' && (
          <form onSubmit={handleUpdateProfile} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Full Name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Enter your name"
                className="workspace-title-input"
                style={{ fontSize: '0.88rem', padding: '9px 12px' }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Bio / Headline</label>
              <input
                type="text"
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                placeholder="e.g. AI Engineer, Researcher, Creative Writer"
                className="workspace-title-input"
                style={{ fontSize: '0.88rem', padding: '9px 12px' }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Default Preferred Persona</label>
              <select
                value={preferredPersona}
                onChange={(e) => setPreferredPersona(e.target.value)}
                className="workspace-title-input"
                style={{ fontSize: '0.88rem', padding: '9px 12px', background: 'var(--bg-input)', color: 'var(--text-primary)' }}
              >
                {PERSONAS.map((p) => (
                  <option key={p.id} value={p.id} style={{ background: '#111827' }}>
                    {p.label} - {p.desc}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Sparkles size={13} style={{ color: 'var(--accent-indigo)' }} /> Custom Instructions for AI
                </label>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Injected into all chat turns</span>
              </div>
              <textarea
                rows={3}
                value={customInstructions}
                onChange={(e) => setCustomInstructions(e.target.value)}
                placeholder="e.g. 'Always respond concisely with bullet points. Cite sources in markdown tables. Include Python typing hints.'"
                className="workspace-prompt-input"
                style={{ fontSize: '0.85rem', padding: '10px 12px', resize: 'vertical' }}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="workspace-action-btn primary"
              style={{
                width: '100%',
                padding: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                fontSize: '0.88rem',
                fontWeight: 600,
                marginTop: '4px'
              }}
            >
              <Save size={15} />
              {loading ? 'Saving...' : 'Save Profile & Preferences'}
            </button>
          </form>
        )}

        {/* TAB: SMART AI MEMORY */}
        {activeTab === 'memory' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Aura AI automatically extracts and retains key personal facts and preferences to personalize responses. You can view, add, or delete memory facts at any time.
            </div>

            {/* Add memory form */}
            <form onSubmit={handleAddMemory} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <input
                type="text"
                value={newFact}
                onChange={(e) => setNewFact(e.target.value)}
                placeholder="e.g. 'I work with Python 3.13 and FastAPI' or 'I prefer concise answers'"
                className="workspace-title-input"
                style={{ flex: 1, fontSize: '0.84rem', padding: '8px 10px' }}
              />
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                className="workspace-title-input"
                style={{ width: '110px', fontSize: '0.8rem', padding: '8px', background: 'var(--bg-input)' }}
              >
                <option value="preference">Preference</option>
                <option value="work">Work</option>
                <option value="project">Project</option>
                <option value="personal">Personal</option>
              </select>
              <button
                type="submit"
                disabled={loading || !newFact.trim()}
                className="workspace-action-btn primary"
                style={{ padding: '8px 12px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '4px' }}
              >
                <Plus size={14} /> Add
              </button>
            </form>

            {/* List of memories */}
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              maxHeight: '240px',
              overflowY: 'auto',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '8px'
            }}>
              {memories.length === 0 ? (
                <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', padding: '16px' }}>
                  No saved memories yet. Start chatting or add a fact above!
                </div>
              ) : (
                memories.map((m) => (
                  <div
                    key={m.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      background: 'rgba(255, 255, 255, 0.03)',
                      padding: '8px 10px',
                      borderRadius: '6px',
                      gap: '8px'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: 0 }}>
                      <span style={{
                        fontSize: '0.68rem',
                        fontWeight: 600,
                        textTransform: 'uppercase',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        background: 'rgba(99, 102, 241, 0.15)',
                        color: 'var(--accent-indigo-light)'
                      }}>
                        {m.category}
                      </span>
                      <span style={{ fontSize: '0.82rem', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {m.fact}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleDeleteMemory(m.id)}
                      style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '4px' }}
                      title="Forget this fact"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))
              )}
            </div>

            {memories.length > 0 && (
              <button
                type="button"
                onClick={handleClearAllMemories}
                style={{
                  alignSelf: 'flex-start',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  textDecoration: 'underline'
                }}
              >
                Forget All AI Memories
              </button>
            )}
          </div>
        )}

        {/* TAB 2: SECURITY & PASSWORD */}
        {activeTab === 'security' && (
          <form onSubmit={handleChangePassword} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Current Password</label>
              <input
                type="password"
                required
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                placeholder="Enter current password"
                className="workspace-title-input"
                style={{ fontSize: '0.88rem', padding: '9px 12px' }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>New Password</label>
              <input
                type="password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Enter new password (min 6 characters)"
                className="workspace-title-input"
                style={{ fontSize: '0.88rem', padding: '9px 12px' }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Confirm New Password</label>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter new password"
                className="workspace-title-input"
                style={{ fontSize: '0.88rem', padding: '9px 12px' }}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="workspace-action-btn primary"
              style={{
                width: '100%',
                padding: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                fontSize: '0.88rem',
                fontWeight: 600,
                marginTop: '4px'
              }}
            >
              <Key size={15} />
              {loading ? 'Updating Password...' : 'Update Password'}
            </button>
          </form>
        )}

        {/* TAB 3: SESSION & HISTORY */}
        {activeTab === 'session' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '14px',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Account Email:</span>
                <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{user.email}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Session Type:</span>
                <span style={{ color: '#6ee7b7', fontWeight: 500 }}>Authenticated JWT Session</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Member Since:</span>
                <span style={{ color: 'var(--text-primary)' }}>
                  {user.created_at ? new Date(user.created_at).toLocaleDateString() : 'Active'}
                </span>
              </div>
            </div>

            <div style={{
              background: 'rgba(99, 102, 241, 0.05)',
              border: '1px solid rgba(99, 102, 241, 0.2)',
              borderRadius: 'var(--radius-sm)',
              padding: '12px',
              fontSize: '0.8rem',
              color: 'var(--text-secondary)'
            }}>
              Your chat history and knowledge documents are isolated to your profile. Logging out will switch the client back to Anonymous Guest Mode.
            </div>

            <button
              type="button"
              onClick={() => {
                if (window.confirm('Are you sure you want to log out?')) {
                  onLogout();
                  onClose();
                }
              }}
              style={{
                width: '100%',
                padding: '10px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                background: 'rgba(239, 68, 68, 0.1)',
                color: '#fca5a5',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              <LogOut size={15} />
              Sign Out (Switch to Guest Mode)
            </button>

            <div style={{
              marginTop: '12px',
              paddingTop: '16px',
              borderTop: '1px dashed rgba(239, 68, 68, 0.25)',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px'
            }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#f87171', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Danger Zone
              </span>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Permanently delete your user account, chats, knowledge base documents, and workspace versions. This action cannot be undone.
              </p>
              <button
                type="button"
                onClick={async () => {
                  if (window.confirm('Are you ABSOLUTELY sure? This will permanently delete your account, all personal chats, documents, and workspace files.')) {
                    try {
                      await api.deleteAccount();
                      alert('Your account and all associated data have been deleted.');
                      onLogout();
                      onClose();
                    } catch (err) {
                      alert(`Account deletion failed: ${err.message}`);
                    }
                  }
                }}
                style={{
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid rgba(239, 68, 68, 0.5)',
                  background: 'transparent',
                  color: '#ef4444',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  textAlign: 'center'
                }}
              >
                Permanently Delete Account
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
