import { useEffect, useState, useCallback } from 'react';
import LoginGate from './components/LoginGate';
import TopBar from './components/TopBar';
import ChatPanel from './components/ChatPanel';
import RoutingTrace from './components/RoutingTrace';
import HandoffModal from './components/HandoffModal';
import { routePrompt, fetchHealth, RouterApiError } from './lib/api';
import { resolveDestination } from './lib/modelMap';

let messageId = 0;
const nextId = () => `m-${++messageId}`;

export default function App() {
  const [session, setSession] = useState(null);
  const [health, setHealth] = useState(null);
  const [messages, setMessages] = useState([]);
  const [status, setStatus] = useState('idle'); // idle | running | done | error
  const [latestResult, setLatestResult] = useState(null);
  const [latestError, setLatestError] = useState(null);
  const [latestDestination, setLatestDestination] = useState(null);
  const [handoffMessage, setHandoffMessage] = useState(null);

  useEffect(() => {
    const stored = sessionStorage.getItem('trust-router-session');
    if (stored) {
      try {
        setSession(JSON.parse(stored));
      } catch {
        sessionStorage.removeItem('trust-router-session');
      }
    }
  }, []);

  useEffect(() => {
    if (!session) return;
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, [session]);

  const handleSubmit = useCallback(async (prompt) => {
    setMessages((prev) => [...prev, { id: nextId(), role: 'user', text: prompt }]);
    setStatus('running');
    setLatestError(null);

    try {
      const result = await routePrompt(prompt);
      const destination = resolveDestination(result.selected_model);
      setLatestResult(result);
      setLatestDestination(destination);
      setStatus('done');
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: 'router',
          prompt,
          selectedModel: result.selected_model,
          selectionMode: result.policy.selection_mode,
          destination,
          result,
        },
      ]);
    } catch (err) {
      const description = err instanceof RouterApiError ? err.message : 'Something went wrong routing that prompt.';
      setLatestError(description);
      setStatus('error');
      setMessages((prev) => [...prev, { id: nextId(), role: 'error', text: description }]);
    }
  }, []);

  if (!session) {
    return <LoginGate onAuthenticated={setSession} />;
  }

  return (
    <div className="h-screen flex flex-col" style={{ background: 'var(--paper)' }}>
      <TopBar
        session={session}
        health={health}
        onSignOut={() => {
          sessionStorage.removeItem('trust-router-session');
          setSession(null);
          setMessages([]);
          setStatus('idle');
        }}
      />
      <div className="flex-1 flex min-h-0 flex-col lg:flex-row">
        <ChatPanel
          messages={messages}
          status={status}
          onSubmit={handleSubmit}
          onOpenHandoff={setHandoffMessage}
        />
        <RoutingTrace status={status} result={latestResult} error={latestError} destination={latestDestination} />
      </div>
      <HandoffModal message={handoffMessage} onClose={() => setHandoffMessage(null)} />
    </div>
  );
}
