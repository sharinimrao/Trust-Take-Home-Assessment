const STAGES = [
  { key: 'validate', label: 'Request validation' },
  { key: 'features', label: 'Prompt feature extraction' },
  { key: 'predict', label: 'Per-model quality & token predictions' },
  { key: 'policy', label: 'Quality / cost routing policy' },
  { key: 'select', label: 'Selected model' },
];

/**
 * Live pipeline trace mirroring the backend's own README diagram:
 * Prompt -> validation -> features -> predictions -> policy -> selection.
 * `status` is 'idle' | 'running' | 'done' | 'error'.
 */
export default function RoutingTrace({ status, result, error, destination }) {
  return (
    <aside
      className="w-full lg:w-[340px] shrink-0 border-l flex flex-col"
      style={{ borderColor: 'var(--line)', background: '#fff' }}
    >
      <div className="px-5 py-4 border-b" style={{ borderColor: 'var(--line)' }}>
        <div className="font-mono-brand text-xs tracking-[0.15em] uppercase" style={{ color: 'var(--ink-soft)' }}>
          Routing trace
        </div>
      </div>

      <div className="px-5 py-5 flex-1 overflow-y-auto">
        <ol className="space-y-0">
          {STAGES.map((stage, i) => {
            const isLast = i === STAGES.length - 1;
            const lit = status === 'running' || status === 'done' || status === 'error';
            const litSolid = status === 'done' || (status === 'running' && !isLast) || (status === 'error' && !isLast);
            return (
              <li key={stage.key} className="flex gap-3 pb-6 last:pb-0 relative">
                {!isLast && (
                  <span
                    className="absolute left-[7px] top-4 w-px h-full"
                    style={{ background: 'var(--line)' }}
                    aria-hidden="true"
                  />
                )}
                <span
                  className="mt-1 w-3.5 h-3.5 rounded-full shrink-0 z-10 transition-colors duration-300"
                  style={{
                    background: litSolid ? 'var(--signal)' : status === 'error' && isLast ? 'var(--error)' : '#fff',
                    border: `2px solid ${lit ? (status === 'error' && isLast ? 'var(--error)' : 'var(--signal)') : 'var(--line)'}`,
                  }}
                />
                <div>
                  <div className="text-sm" style={{ color: status === 'idle' ? 'var(--ink-soft)' : 'var(--ink)' }}>
                    {stage.label}
                  </div>
                  {stage.key === 'select' && status === 'done' && result && (
                    <div className="mt-2 space-y-2">
                      <div
                        className="inline-flex items-center gap-1.5 font-mono-brand text-xs rounded-md px-2 py-1"
                        style={{ background: 'var(--signal-soft)', color: 'var(--signal)' }}
                      >
                        {result.selected_model}
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        <Badge
                          tone={result.policy.selection_mode === 'scored' ? 'signal' : 'spark'}
                          label={result.policy.selection_mode === 'scored' ? 'Scored pick' : 'Random exploration'}
                        />
                        <Badge tone="neutral" label={`${result.routing_latency_ms.toFixed(1)} ms`} />
                        {destination && (
                          <Badge
                            tone={destination.isFallback ? 'spark' : 'neutral'}
                            label={`→ ${destination.destination}${destination.isFallback ? ' (approx.)' : ''}`}
                          />
                        )}
                      </div>
                    </div>
                  )}
                  {stage.key === 'select' && status === 'error' && (
                    <div className="mt-2 text-xs" style={{ color: 'var(--error)' }}>
                      {error || 'Routing failed'}
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      </div>

      {status === 'done' && result && (
        <div className="border-t px-5 py-4" style={{ borderColor: 'var(--line)' }}>
          <div className="font-mono-brand text-xs tracking-[0.15em] uppercase mb-3" style={{ color: 'var(--ink-soft)' }}>
            Candidate scores
          </div>
          <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
            {[...result.candidates]
              .sort((a, b) => b.utility - a.utility)
              .map((candidate) => (
                <div key={candidate.model} className="flex items-center gap-2">
                  <div
                    className="flex-1 text-xs font-mono-brand truncate"
                    style={{
                      color: candidate.model === result.selected_model ? 'var(--signal)' : 'var(--ink-soft)',
                      fontWeight: candidate.model === result.selected_model ? 600 : 400,
                    }}
                    title={candidate.model}
                  >
                    {candidate.model}
                  </div>
                  <div className="w-16 h-1.5 rounded-full overflow-hidden shrink-0" style={{ background: 'var(--line)' }}>
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${Math.max(4, candidate.predicted_quality * 100)}%`,
                        background: candidate.model === result.selected_model ? 'var(--signal)' : 'var(--ink-soft)',
                      }}
                    />
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}
    </aside>
  );
}

function Badge({ tone, label }) {
  const tones = {
    signal: { background: 'var(--signal-soft)', color: 'var(--signal)' },
    spark: { background: 'var(--spark-soft)', color: 'var(--spark)' },
    neutral: { background: 'var(--paper)', color: 'var(--ink-soft)', border: '1px solid var(--line)' },
  };
  return (
    <span className="font-mono-brand text-[11px] rounded-md px-1.5 py-0.5" style={tones[tone]}>
      {label}
    </span>
  );
}
