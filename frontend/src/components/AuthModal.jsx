import React, { useState } from 'react';
import { 
  X, LogIn, UserPlus, KeyRound, Mail, Lock, User, 
  CheckCircle2, AlertCircle, ArrowRight 
} from 'lucide-react';
import { api } from '../services/api';
import { getOrCreateSessionId } from '../utils/session';

export default function AuthModal({ isOpen, onClose, onAuthSuccess, initialMode = 'login' }) {
  const [mode, setMode] = useState(initialMode); // 'login' | 'register' | 'forgot'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [claimGuest, setClaimGuest] = useState(true);
  
  // Forgot / Reset password state
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [resetStep, setResetStep] = useState(1); // 1 = request token, 2 = enter token + new password
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  if (!isOpen) return null;

  const resetForm = () => {
    setError('');
    setSuccessMsg('');
    setPassword('');
    setNewPassword('');
    setResetToken('');
  };

  const switchMode = (newMode) => {
    resetForm();
    setMode(newMode);
    setResetStep(1);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please provide both email and password.');
      return;
    }

    try {
      setLoading(true);
      setError('');
      const guestSessionId = claimGuest ? getOrCreateSessionId() : undefined;
      const res = await api.login({
        email,
        password,
        claim_guest_session_id: guestSessionId
      });
      if (onAuthSuccess) onAuthSuccess(res.user);
      onClose();
    } catch (err) {
      setError(err.message || 'Login failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Email and password are required.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    try {
      setLoading(true);
      setError('');
      const guestSessionId = claimGuest ? getOrCreateSessionId() : undefined;
      const res = await api.register({
        email,
        password,
        full_name: fullName,
        claim_guest_session_id: guestSessionId
      });
      if (onAuthSuccess) onAuthSuccess(res.user);
      onClose();
    } catch (err) {
      setError(err.message || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleRequestResetToken = async (e) => {
    e.preventDefault();
    if (!email) {
      setError('Please enter your account email.');
      return;
    }

    try {
      setLoading(true);
      setError('');
      const res = await api.forgotPassword(email);
      setSuccessMsg(res.message || 'Reset token generated.');
      if (res.reset_token) {
        setResetToken(res.reset_token);
      }
      setResetStep(2);
    } catch (err) {
      setError(err.message || 'Could not initiate password reset.');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmReset = async (e) => {
    e.preventDefault();
    if (!resetToken || !newPassword) {
      setError('Reset token and new password are required.');
      return;
    }
    if (newPassword.length < 6) {
      setError('New password must be at least 6 characters.');
      return;
    }

    try {
      setLoading(true);
      setError('');
      const res = await api.resetPassword({
        email,
        reset_token: resetToken,
        new_password: newPassword
      });
      setSuccessMsg(res.message + ' You can now sign in.');
      setTimeout(() => {
        switchMode('login');
      }, 1500);
    } catch (err) {
      setError(err.message || 'Failed to reset password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div 
        className="modal-card" 
        onClick={(e) => e.stopPropagation()} 
        style={{ maxWidth: '440px', position: 'relative' }}
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

        {/* Modal Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div 
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white'
            }}
          >
            {mode === 'login' && <LogIn size={18} />}
            {mode === 'register' && <UserPlus size={18} />}
            {mode === 'forgot' && <KeyRound size={18} />}
          </div>
          <div>
            <h3 className="modal-title" style={{ margin: 0, fontSize: '1.2rem' }}>
              {mode === 'login' && 'Welcome Back'}
              {mode === 'register' && 'Create Account'}
              {mode === 'forgot' && 'Reset Password'}
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              {mode === 'login' && 'Sign in to access your personal history & settings'}
              {mode === 'register' && 'Create a profile to sync chats & custom prompts'}
              {mode === 'forgot' && 'Regain access using a secure recovery code'}
            </p>
          </div>
        </div>

        {/* Status Alerts */}
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

        {/* Tab Switcher (Login / Register) */}
        {mode !== 'forgot' && (
          <div style={{
            display: 'flex',
            background: 'rgba(255, 255, 255, 0.04)',
            borderRadius: 'var(--radius-sm)',
            padding: '4px',
            gap: '4px'
          }}>
            <button
              type="button"
              onClick={() => switchMode('login')}
              style={{
                flex: 1,
                padding: '8px 12px',
                borderRadius: '6px',
                border: 'none',
                background: mode === 'login' ? 'var(--accent-indigo)' : 'transparent',
                color: mode === 'login' ? '#fff' : 'var(--text-secondary)',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.85rem'
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => switchMode('register')}
              style={{
                flex: 1,
                padding: '8px 12px',
                borderRadius: '6px',
                border: 'none',
                background: mode === 'register' ? 'var(--accent-indigo)' : 'transparent',
                color: mode === 'register' ? '#fff' : 'var(--text-secondary)',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.85rem'
              }}
            >
              Create Account
            </button>
          </div>
        )}

        {/* LOGIN FORM */}
        {mode === 'login' && (
          <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Mail size={13} /> Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                className="workspace-title-input"
                style={{ fontSize: '0.9rem', padding: '10px 12px' }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Lock size={13} /> Password
                </label>
                <button
                  type="button"
                  onClick={() => switchMode('forgot')}
                  style={{ background: 'none', border: 'none', color: 'var(--accent-indigo-light)', fontSize: '0.75rem', cursor: 'pointer' }}
                >
                  Forgot password?
                </button>
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                className="workspace-title-input"
                style={{ fontSize: '0.9rem', padding: '10px 12px' }}
              />
            </div>

            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={claimGuest}
                onChange={(e) => setClaimGuest(e.target.checked)}
                style={{ accentColor: 'var(--accent-indigo)' }}
              />
              <span>Merge current guest chat history into account</span>
            </label>

            <button
              type="submit"
              disabled={loading}
              className="workspace-action-btn primary"
              style={{
                width: '100%',
                padding: '11px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                fontSize: '0.9rem',
                fontWeight: 600
              }}
            >
              {loading ? 'Signing in...' : 'Sign In'}
              {!loading && <ArrowRight size={15} />}
            </button>
          </form>
        )}

        {/* REGISTER FORM */}
        {mode === 'register' && (
          <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <User size={13} /> Full Name (Optional)
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="e.g. Alex Mercer"
                className="workspace-title-input"
                style={{ fontSize: '0.9rem', padding: '10px 12px' }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Mail size={13} /> Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                className="workspace-title-input"
                style={{ fontSize: '0.9rem', padding: '10px 12px' }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Lock size={13} /> Password (min 6 characters)
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Choose a strong password"
                className="workspace-title-input"
                style={{ fontSize: '0.9rem', padding: '10px 12px' }}
              />
            </div>

            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={claimGuest}
                onChange={(e) => setClaimGuest(e.target.checked)}
                style={{ accentColor: 'var(--accent-indigo)' }}
              />
              <span>Migrate existing guest conversations into account</span>
            </label>

            <button
              type="submit"
              disabled={loading}
              className="workspace-action-btn primary"
              style={{
                width: '100%',
                padding: '11px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                fontSize: '0.9rem',
                fontWeight: 600
              }}
            >
              {loading ? 'Creating account...' : 'Create Account'}
              {!loading && <ArrowRight size={15} />}
            </button>
          </form>
        )}

        {/* FORGOT PASSWORD FORM */}
        {mode === 'forgot' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {resetStep === 1 ? (
              <form onSubmit={handleRequestResetToken} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Mail size={13} /> Account Email
                  </label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter your registered email"
                    className="workspace-title-input"
                    style={{ fontSize: '0.9rem', padding: '10px 12px' }}
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="workspace-action-btn primary"
                  style={{
                    width: '100%',
                    padding: '11px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    fontSize: '0.9rem'
                  }}
                >
                  {loading ? 'Generating Code...' : 'Send Recovery Code'}
                  {!loading && <KeyRound size={15} />}
                </button>
              </form>
            ) : (
              <form onSubmit={handleConfirmReset} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    Recovery Reset Token
                  </label>
                  <input
                    type="text"
                    required
                    value={resetToken}
                    onChange={(e) => setResetToken(e.target.value)}
                    placeholder="Paste reset token"
                    className="workspace-title-input"
                    style={{ fontSize: '0.85rem', padding: '10px 12px', fontFamily: 'monospace' }}
                  />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Lock size={13} /> New Password
                  </label>
                  <input
                    type="password"
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Enter at least 6 characters"
                    className="workspace-title-input"
                    style={{ fontSize: '0.9rem', padding: '10px 12px' }}
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="workspace-action-btn primary"
                  style={{
                    width: '100%',
                    padding: '11px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    fontSize: '0.9rem'
                  }}
                >
                  {loading ? 'Resetting...' : 'Set New Password'}
                </button>
              </form>
            )}

            <button
              type="button"
              onClick={() => switchMode('login')}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                fontSize: '0.8rem',
                cursor: 'pointer',
                textAlign: 'center',
                marginTop: '4px'
              }}
            >
              Back to Sign In
            </button>
          </div>
        )}

        {/* Guest Mode Fallback */}
        <div style={{
          borderTop: '1px solid var(--border-subtle)',
          paddingTop: '12px',
          textAlign: 'center'
        }}>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              fontSize: '0.8rem',
              cursor: 'pointer',
              textDecoration: 'underline'
            }}
          >
            Continue as Guest (No account needed)
          </button>
        </div>
      </div>
    </div>
  );
}
