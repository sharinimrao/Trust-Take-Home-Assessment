export default function TopBar({ session, onSignOut, health }) {
  return (
    <header
      className="h-14 shrink-0 border-b flex items-center justify-between px-6"
      style={{ borderColor: 'var(--line)', background: '#fff' }}
    >
      <div className="flex items-center gap-2.5">
        <span className="font-mono-brand text-sm font-semibold tracking-[0.1em]" style={{ color: 'var(--ink)' }}>
          TRUST<span style={{ color: 'var(--signal)' }}>ROUTER</span>
        </span>
        <StatusDot ok={health?.status === 'ok'} />
      </div>

      <div className="flex items-center gap-3">
        <span className="text-sm" style={{ color: 'var(--ink-soft)' }}>
          {session.name}
        </span>
        <button
          type="button"
          onClick={onSignOut}
          className="text-xs font-medium rounded-lg border px-2.5 py-1.5 transition-colors hover:bg-gray-50"
          style={{ borderColor: 'var(--line)', color: 'var(--ink-soft)' }}
        >
          Sign out
        </button>
      </div>
    </header>
  );
}

function StatusDot({ ok }) {
  return (
    <span
      className="w-1.5 h-1.5 rounded-full"
      style={{ background: ok ? '#2f9e5b' : 'var(--ink-soft)' }}
      title={ok ? 'Router online' : 'Router status unknown'}
    />
  );
}
