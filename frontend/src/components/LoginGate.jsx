import { useState } from 'react';

/**
 * Client-side login gate. There is no auth backend in this take-home
 * (see README) so this only validates shape and stores a session in
 * memory + sessionStorage. It exists to satisfy the requested login flow,
 * not as a real security boundary.
 *
 * Visual direction matches trytrust.ai directly: a deep teal hero panel,
 * a bold condensed display headline, and the faceted/triangulated line
 * motif from their homepage — which doubles here as a nod to "routing":
 * lines connecting nodes toward a destination.
 */
export default function LoginGate({ onAuthenticated }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState(null);

  function handleSubmit(event) {
    event.preventDefault();
    const trimmedName = name.trim();
    const trimmedEmail = email.trim();

    if (!trimmedName) {
      setError('Enter your name to continue.');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      setError('Enter a valid email address.');
      return;
    }

    setError(null);
    const session = { name: trimmedName, email: trimmedEmail };
    sessionStorage.setItem('trust-router-session', JSON.stringify(session));
    onAuthenticated(session);
  }

  return (
    <div className="min-h-screen flex flex-col lg:flex-row">
      {/* Hero panel */}
      <div
        className="relative overflow-hidden flex-1 flex flex-col justify-between px-8 py-10 lg:px-14 lg:py-14 min-h-[280px]"
        style={{ background: 'var(--signal)' }}
      >
        <FacetedLines />
        <div className="relative z-10">
          <div className="font-mono-brand text-xs tracking-[0.2em] uppercase text-white/70">Take Home Router</div>
        </div>
        <div className="relative z-10 max-w-md">
          <h1 className="font-display-brand text-white text-5xl lg:text-6xl leading-[0.95]">
            Route every prompt.
          </h1>
          <p className="mt-5 text-white/85 text-base leading-relaxed max-w-sm">
            Every request is scored against the model catalog, then sent to the candidate that clears the bar —
            watch the decision happen in real time.
          </p>
        </div>
      </div>

      {/* Form panel */}
      <div className="flex items-center justify-center px-6 py-12 lg:w-[420px] shrink-0" style={{ background: 'var(--paper)' }}>
        <div className="w-full max-w-sm">
          <h2 className="text-2xl font-semibold" style={{ color: 'var(--ink)' }}>
            Sign in to continue
          </h2>
          <p className="mt-2 text-sm" style={{ color: 'var(--ink-soft)' }}>
            This is a local demo gate — no account is created or verified.
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label htmlFor="name" className="block text-xs font-medium mb-1.5" style={{ color: 'var(--ink-soft)' }}>
                Name
              </label>
              <input
                id="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ada Lovelace"
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors"
                style={{ borderColor: 'var(--line)' }}
                autoComplete="name"
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-xs font-medium mb-1.5" style={{ color: 'var(--ink-soft)' }}>
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ada@example.com"
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors"
                style={{ borderColor: 'var(--line)' }}
                autoComplete="email"
              />
            </div>

            {error && (
              <div
                role="alert"
                className="text-sm rounded-lg px-3 py-2"
                style={{ background: 'var(--error-soft)', color: 'var(--error)' }}
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              className="w-full rounded-lg py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90"
              style={{ background: 'var(--signal)' }}
            >
              Continue
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

/** Faceted triangulated line pattern, echoing trytrust.ai's hero graphic. */
function FacetedLines() {
  return (
    <svg
      className="absolute inset-0 w-full h-full pointer-events-none"
      viewBox="0 0 800 600"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      <g stroke="rgba(255,255,255,0.35)" strokeWidth="1.5" fill="none">
        <path d="M560 40 L 720 260 L 480 340 Z" />
        <path d="M720 260 L 640 480 L 480 340 Z" />
        <path d="M480 340 L 640 480 L 380 560 Z" />
        <path d="M560 40 L 480 340" />
        <path d="M720 260 L 800 120" />
        <path d="M640 480 L 800 520" />
        <path d="M380 560 L 260 600" />
      </g>
      <g fill="rgba(255,255,255,0.9)">
        <circle cx="560" cy="40" r="3" />
        <circle cx="720" cy="260" r="3" />
        <circle cx="480" cy="340" r="3" />
        <circle cx="640" cy="480" r="3" />
        <circle cx="380" cy="560" r="3" />
      </g>
    </svg>
  );
}
