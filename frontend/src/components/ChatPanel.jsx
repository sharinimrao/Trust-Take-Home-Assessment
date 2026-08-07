import { useEffect, useRef, useState } from 'react';

export default function ChatPanel({ messages, status, onSubmit, onOpenHandoff }) {
  const [draft, setDraft] = useState('');
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, status]);

  function handleSubmit(event) {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || status === 'running') return;
    onSubmit(trimmed);
    setDraft('');
  }

  return (
    <div className="flex-1 flex flex-col min-w-0">
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-6">
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="max-w-2xl mx-auto space-y-5">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} onOpenHandoff={onOpenHandoff} />
            ))}
            {status === 'running' && <LoadingBubble />}
          </div>
        )}
      </div>

      <div className="border-t px-6 py-4" style={{ borderColor: 'var(--line)' }}>
        <form onSubmit={handleSubmit} className="max-w-2xl mx-auto flex gap-2 items-end">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            placeholder="Ask something — routing decides which model handles it."
            rows={1}
            className="flex-1 resize-none rounded-xl border px-4 py-3 text-sm outline-none"
            style={{ borderColor: 'var(--line)', maxHeight: 160 }}
          />
          <button
            type="submit"
            disabled={!draft.trim() || status === 'running'}
            className="rounded-xl px-4 py-3 text-sm font-medium text-white shrink-0 transition-opacity disabled:opacity-40"
            style={{ background: 'var(--signal)' }}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="h-full flex items-center justify-center text-center px-6">
      <div className="max-w-xs">
        <div className="font-mono-brand text-xs tracking-[0.15em] uppercase mb-2" style={{ color: 'var(--signal)' }}>
          Take Home Router
        </div>
        <p className="text-sm" style={{ color: 'var(--ink-soft)' }}>
          Every prompt is scored against the model catalog before anything runs. Send one to see the routing
          decision trace on the right.
        </p>
      </div>
    </div>
  );
}

function MessageBubble({ message, onOpenHandoff }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm px-4 py-2.5 text-sm text-white" style={{ background: 'var(--ink)' }}>
          {message.text}
        </div>
      </div>
    );
  }

  if (message.role === 'error') {
    return (
      <div className="flex justify-start">
        <div
          className="max-w-[80%] rounded-2xl rounded-bl-sm px-4 py-2.5 text-sm"
          style={{ background: 'var(--error-soft)', color: 'var(--error)' }}
        >
          {message.text}
        </div>
      </div>
    );
  }

  // role: 'router'
  return (
    <div className="flex justify-start">
      <div
        className="max-w-[80%] rounded-2xl rounded-bl-sm px-4 py-3 text-sm border"
        style={{ borderColor: 'var(--line)', background: '#fff' }}
      >
        <div className="flex items-center gap-2 mb-1.5">
          <span className="font-mono-brand text-xs font-semibold" style={{ color: 'var(--signal)' }}>
            {message.selectedModel}
          </span>
          <span
            className="font-mono-brand text-[10px] rounded px-1.5 py-0.5"
            style={{
              background: message.selectionMode === 'scored' ? 'var(--signal-soft)' : 'var(--spark-soft)',
              color: message.selectionMode === 'scored' ? 'var(--signal)' : 'var(--spark)',
            }}
          >
            {message.selectionMode}
          </span>
        </div>
        <p style={{ color: 'var(--ink-soft)' }}>
          This prompt was routed to <strong style={{ color: 'var(--ink)' }}>{message.selectedModel}</strong>. This
          demo classifies and selects a model — it doesn't generate a reply itself.
        </p>
        <button
          type="button"
          onClick={() => onOpenHandoff(message)}
          className="mt-2.5 text-xs font-medium underline underline-offset-2"
          style={{ color: 'var(--signal)' }}
        >
          Hand off to {message.destination?.destination ?? 'provider'} →
        </button>
      </div>
    </div>
  );
}

function LoadingBubble() {
  return (
    <div className="flex justify-start">
      <div
        className="rounded-2xl rounded-bl-sm px-4 py-3 text-sm border flex items-center gap-1.5"
        style={{ borderColor: 'var(--line)', background: '#fff', color: 'var(--ink-soft)' }}
      >
        <Dot delay="0ms" />
        <Dot delay="150ms" />
        <Dot delay="300ms" />
      </div>
    </div>
  );
}

function Dot({ delay }) {
  return (
    <span
      className="w-1.5 h-1.5 rounded-full animate-bounce"
      style={{ background: 'var(--ink-soft)', animationDelay: delay }}
    />
  );
}
