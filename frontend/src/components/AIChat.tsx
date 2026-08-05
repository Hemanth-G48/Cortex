import { useEffect, useRef, useState } from 'react';
import { endpoints } from '../services/api';
import { onAIChatToggle } from '../utils/aiChatBus';

interface Message {
  role: 'user' | 'ai';
  text: string;
}

const QUICK_PROMPTS = [
  'What are my upcoming deadlines?',
  'Give me a study tip',
  'How are my grades looking?',
  'Help',
];

export const AIChat = () => {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'ai',
      text: "Hey! I'm Shiori, your AI study companion. Ask me about your assignments, deadlines, grades, or study plans!",
    },
  ]);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const off = onAIChatToggle(() => setOpen((o) => !o));
    return off;
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [messages, typing, open]);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || typing) return;
    setMessages((m) => [...m, { role: 'user', text: trimmed }]);
    setInput('');
    setTyping(true);
    try {
      const res = await endpoints.ai.chat({ message: trimmed });
      setMessages((m) => [...m, { role: 'ai', text: res.message }]);
    } catch {
      setMessages((m) => [...m, { role: 'ai', text: "Sorry — I couldn't reach the assistant. Check that the backend is running." }]);
    }
    setTyping(false);
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open AI assistant"
        className="ai-chat-fab"
        style={{
          position: 'fixed',
          bottom: '1.5rem',
          right: '1.5rem',
          zIndex: 900,
          width: 56,
          height: 56,
          borderRadius: '50%',
          border: 'none',
          background: 'linear-gradient(135deg, var(--accent), var(--info))',
          color: '#fff',
          fontSize: '1.5rem',
          cursor: 'pointer',
          boxShadow: '0 8px 24px rgba(0,0,0,0.45)',
          transition: 'transform 0.15s ease, box-shadow 0.15s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'scale(1.06)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
        }}
      >
        🤖
      </button>
    );
  }

  return (
    <div
      className="fade-in"
      style={{
        position: 'fixed',
        bottom: '1.5rem',
        right: '1.5rem',
        zIndex: 900,
        width: 'min(380px, calc(100vw - 3rem))',
        height: 'min(520px, calc(100vh - 6rem))',
        background: 'var(--bg-card)',
        border: '1px solid var(--border-light)',
        borderRadius: 16,
        display: 'flex',
        flexDirection: 'column',
        boxShadow: 'var(--shadow-lg)',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.6rem',
          padding: '0.85rem 1rem',
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg-hover)',
        }}
      >
        <span style={{ fontSize: '1.2rem' }}>🤖</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>Shiori Assistant</div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Ctrl+K to toggle</div>
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setOpen(false)} aria-label="Close AI assistant">
          ✕
        </button>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              maxWidth: '85%',
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
              padding: '0.55rem 0.8rem',
              borderRadius: 12,
              fontSize: '0.8rem',
              lineHeight: 1.45,
              whiteSpace: 'pre-wrap',
              background: m.role === 'user' ? 'var(--accent-muted)' : 'var(--bg-primary)',
              border: `1px solid ${m.role === 'user' ? 'var(--accent)' : 'var(--border)'}`,
              color: 'var(--text-primary)',
            }}
          >
            {m.text}
          </div>
        ))}
        {typing && (
          <div
            style={{
              alignSelf: 'flex-start',
              padding: '0.55rem 0.8rem',
              borderRadius: 12,
              fontSize: '0.8rem',
              background: 'var(--bg-primary)',
              border: '1px solid var(--border)',
              color: 'var(--text-muted)',
            }}
          >
            <span className="ai-typing">Shiori is typing…</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Quick prompts */}
      <div style={{ display: 'flex', gap: '0.35rem', padding: '0 0.85rem 0.5rem', flexWrap: 'wrap' }}>
        {QUICK_PROMPTS.map((q) => (
          <button
            key={q}
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => void send(q)}
            disabled={typing}
            style={{ fontSize: '0.68rem' }}
          >
            {q}
          </button>
        ))}
      </div>

      {/* Input */}
      <div style={{ display: 'flex', gap: '0.5rem', padding: '0.6rem 0.85rem 0.85rem', borderTop: '1px solid var(--border)' }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && void send(input)}
          placeholder="Ask about your study life…"
          style={{ flex: 1, fontSize: '0.8rem' }}
        />
        <button type="button" className="btn btn-primary" onClick={() => void send(input)} disabled={!input.trim() || typing}>
          ➤
        </button>
      </div>
    </div>
  );
};
