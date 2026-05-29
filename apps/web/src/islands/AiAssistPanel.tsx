import { useState } from 'react';
import { useStore } from '~/lib/store';

interface Props { field: string; onClose: () => void }

const BASE = (import.meta.env.PUBLIC_API_BASE as string | undefined) ?? 'http://localhost:8000';

export default function AiAssistPanel({ field, onClose }: Props) {
  const card = useStore((s) => ({ ...(s.sourceCard ?? {}), ...(s.converted ?? {}), ...s.overrides }));
  const setOverride = useStore((s) => s.setOverride);
  const [text, setText] = useState('');
  const [status, setStatus] = useState<'idle' | 'streaming' | 'done' | 'error'>('idle');

  async function generate() {
    setText(''); setStatus('streaming');
    try {
      const res = await fetch(`${BASE}/api/ai/enrich`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ card, field }),
      });
      if (!res.ok || !res.body) throw new Error(`${res.status}`);
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
          if (m) setText((prev) => prev + m[1]);
        }
      }
      setStatus('done');
    } catch {
      setStatus('error');
    }
  }

  function accept() { setOverride(field, text.trim()); onClose(); }

  return (
    <aside role="dialog" aria-label={`AI assist for ${field}`}
      className="fixed right-0 top-0 h-full w-96 bg-white border-l shadow-xl p-4 space-y-3 overflow-y-auto">
      <header className="flex justify-between items-center">
        <h3 className="font-medium">AI assist · {field}</h3>
        <button type="button" onClick={onClose} aria-label="Close" className="text-slate-500">×</button>
      </header>
      <div className="text-xs text-slate-500">Uses other card fields as context.</div>
      <button type="button" onClick={generate}
        disabled={status === 'streaming'}
        className="px-3 py-1 bg-slate-900 text-white rounded text-sm disabled:opacity-40">
        {status === 'streaming' ? 'Streaming…' : status === 'done' ? 'Regenerate' : 'Generate'}
      </button>
      <pre className="whitespace-pre-wrap text-sm border rounded p-2 min-h-32 bg-slate-50">{text}</pre>
      {status === 'error' && <p className="text-sm text-red-600">Stream failed. Try again.</p>}
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
