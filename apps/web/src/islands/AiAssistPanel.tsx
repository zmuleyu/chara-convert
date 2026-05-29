import { useState } from 'react';
import { useStore } from '~/lib/store';
import { useBilling } from '~/lib/billing/client';
import { MIN_BALANCE_TO_TRY } from '~/lib/billing/constants';
import LowCreditCTA from './LowCreditCTA';

interface Props { field: string; onClose: () => void }

const BASE = (import.meta.env.PUBLIC_API_BASE as string | undefined) ?? 'http://localhost:8000';

type ErrorKind =
  | { kind: 'none' }
  | { kind: 'insufficient_credit'; message: string }
  | { kind: 'service_unavailable'; message: string }
  | { kind: 'generic'; message: string };

function describeError(code: string | undefined, fallback: string): ErrorKind {
  if (code === 'insufficient_credit') {
    return { kind: 'insufficient_credit', message: 'Out of credits. Top up to keep going.' };
  }
  if (code === 'service_unavailable' || code === 'internal_error') {
    return { kind: 'service_unavailable', message: 'Billing service is temporarily down. Try again in a moment.' };
  }
  return { kind: 'generic', message: fallback };
}

export default function AiAssistPanel({ field, onClose }: Props) {
  const card = useStore((s) => ({ ...(s.sourceCard ?? {}), ...(s.converted ?? {}), ...s.overrides }));
  const setOverride = useStore((s) => s.setOverride);
  const billing = useBilling();
  const lowCredit = billing.loaded && billing.balance < MIN_BALANCE_TO_TRY;
  const [text, setText] = useState('');
  const [status, setStatus] = useState<'idle' | 'streaming' | 'done' | 'error'>('idle');
  const [errorInfo, setErrorInfo] = useState<ErrorKind>({ kind: 'none' });

  async function generate() {
    if (!billing.userId) {
      // Defense in depth: useBilling auto-generates a userId via
      // getOrCreateUserId, so null here implies SSR / non-browser context that
      // shouldn't reach this handler.
      setErrorInfo({ kind: 'generic', message: 'No user id available.' });
      setStatus('error');
      return;
    }
    setText(''); setStatus('streaming'); setErrorInfo({ kind: 'none' });
    try {
      const res = await fetch(`${BASE}/api/ai/enrich`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': billing.userId,
        },
        body: JSON.stringify({ card, field }),
      });

      // Pre-stream error envelope (FastAPI returns JSONResponse before opening SSE)
      const contentType = res.headers.get('content-type') ?? '';
      if (!res.ok && contentType.includes('application/json')) {
        const body = await res.json().catch(() => ({}));
        setErrorInfo(describeError(body.code, body.message ?? `HTTP ${res.status}`));
        setStatus('error');
        return;
      }
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = '';
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const events = buf.split('\n\n');
        buf = events.pop() ?? '';
        for (const ev of events) {
          const m = ev.match(/^data:\s?(.*)$/m);
          if (!m) continue;
          const data = m[1];
          // Mid-stream error frame from ai_enrich.py: {"event":"error","code":...,"message":...}
          if (data.startsWith('{') && data.includes('"event"')) {
            try {
              const parsed = JSON.parse(data);
              if (parsed.event === 'error') {
                setErrorInfo(describeError(parsed.code, parsed.message ?? 'Stream failed.'));
                setStatus('error');
                return;
              }
            } catch { /* not a JSON event, fall through to content append */ }
          }
          if (data === '[DONE]') continue;
          setText((prev) => prev + data);
        }
      }
      setStatus('done');
    } catch (e) {
      setErrorInfo({ kind: 'generic', message: (e as Error).message || 'Stream failed.' });
      setStatus('error');
    }
  }

  function accept() { setOverride(field, text.trim()); onClose(); }

  const buttonLabel = !billing.loaded
    ? 'Loading…'
    : lowCredit
      ? 'Low credit'
      : status === 'streaming'
        ? 'Streaming…'
        : status === 'done'
          ? 'Regenerate'
          : 'Generate';

  return (
    <aside role="dialog" aria-label={`AI assist for ${field}`}
      className="fixed right-0 top-0 h-full w-96 bg-white border-l shadow-xl p-4 space-y-3 overflow-y-auto">
      <header className="flex justify-between items-center">
        <h3 className="font-medium">AI assist · {field}</h3>
        <button type="button" onClick={onClose} aria-label="Close" className="text-slate-500">×</button>
      </header>
      <div className="text-xs text-slate-500">Uses other card fields as context.</div>
      <button type="button" onClick={generate}
        disabled={!billing.loaded || lowCredit || status === 'streaming'}
        className="px-3 py-1 bg-slate-900 text-white rounded text-sm disabled:opacity-40">
        {buttonLabel}
      </button>
      {lowCredit && <LowCreditCTA />}
      <pre className="whitespace-pre-wrap text-sm border rounded p-2 min-h-32 bg-slate-50">{text}</pre>
      {status === 'error' && errorInfo.kind === 'insufficient_credit' && (
        <div className="text-sm text-amber-700 border border-amber-300 bg-amber-50 rounded p-2">
          {errorInfo.message}
        </div>
      )}
      {status === 'error' && errorInfo.kind === 'service_unavailable' && (
        <p className="text-sm text-amber-700">{errorInfo.message}</p>
      )}
      {status === 'error' && errorInfo.kind === 'generic' && (
        <p className="text-sm text-red-600">{errorInfo.message}</p>
      )}
      <div className="flex gap-2">
        <button type="button" disabled={!text} onClick={accept}
          className="px-3 py-1 bg-emerald-600 text-white rounded text-sm disabled:opacity-40">
          Accept
        </button>
        <button type="button" onClick={onClose} className="px-3 py-1 border rounded text-sm">Reject</button>
      </div>
    </aside>
  );
}
