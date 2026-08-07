import { useState } from 'react';

const DESTINATION_URLS = {
  'claude.ai': 'https://claude.ai/new',
  'chatgpt.com': 'https://chatgpt.com/',
};

export default function HandoffModal({ message, onClose }) {
  const [copied, setCopied] = useState(false);
  if (!message) return null;

  const destination = message.destination;
  const url = DESTINATION_URLS[destination?.destination] ?? DESTINATION_URLS['chatgpt.com'];

  async function handleCopyAndOpen() {
    try {
      await navigator.clipboard.writeText(message.prompt);
      setCopied(true);
    } catch {
      // clipboard may be blocked; user can still copy manually below
    }
    window.open(url, '_blank', 'noopener,noreferrer');
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
      style={{ background: 'rgba(16, 21, 28, 0.45)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl border bg-white p-6"
        style={{ borderColor: 'var(--line)' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="font-mono-brand text-xs tracking-[0.15em] uppercase mb-1" style={{ color: 'var(--ink-soft)' }}>
          Hand off
        </div>
        <h2 className="text-lg font-semibold mb-1" style={{ color: 'var(--ink)' }}>
          Send to {destination?.destination}
        </h2>
        <p className="text-sm mb-4" style={{ color: 'var(--ink-soft)' }}>
          Routed to <strong style={{ color: 'var(--ink)' }}>{message.selectedModel}</strong>
          {destination?.isFallback && ' (approximated — this model has no direct claude.ai/chatgpt.com equivalent)'}.
          Neither site accepts a prompt via URL, so this copies your prompt and opens the site — paste with{' '}
          <kbd className="px-1 py-0.5 rounded border text-xs" style={{ borderColor: 'var(--line)' }}>
            ⌘/Ctrl+V
          </kbd>
          . The companion userscript (see README) automates this step.
        </p>

        <div
          className="rounded-lg border px-3 py-2 text-xs font-mono-brand max-h-28 overflow-y-auto mb-4"
          style={{ borderColor: 'var(--line)', background: 'var(--paper)', color: 'var(--ink-soft)' }}
        >
          {message.prompt}
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-lg py-2 text-sm font-medium border"
            style={{ borderColor: 'var(--line)', color: 'var(--ink-soft)' }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleCopyAndOpen}
            className="flex-1 rounded-lg py-2 text-sm font-medium text-white"
            style={{ background: 'var(--signal)' }}
          >
            {copied ? 'Copied — opening…' : `Copy & open ${destination?.destination}`}
          </button>
        </div>
      </div>
    </div>
  );
}
