import { useState } from 'react';

/**
 * Client-side login gate. There is no auth backend in this take-home
 * (see README) so this only validates shape and stores a session in
 * memory + sessionStorage. It exists to satisfy the requested login flow,
 * not as a real security boundary.
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
    <div className="min-h-screen flex items-center justify-center px-6" style={{ background: 'var(--paper)' }}>
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="font-mono-brand text-sm tracking-[0.2em] uppercase" style={{ color: 'var(--signal)' }}>
            Take Home Router
          </div>
          <h1 className="mt-3 text-2xl font-semibold" style={{ color: 'var(--ink)' }}>
            Sign in to continue
          </h1>
          <p className="mt-2 text-sm" style={{ color: 'var(--ink-soft)' }}>
            This is a local demo gate — no account is created or verified.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="border rounded-xl p-6 space-y-4"
          style={{ borderColor: 'var(--line)', background: '#fff' }}
        >
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
  );
}
