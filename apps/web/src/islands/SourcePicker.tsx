import { useState } from 'react';
import { api } from '~/lib/api';
import { useStore } from '~/lib/store';

export default function SourcePicker() {
  const [raw, setRaw] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const detected = useStore((s) => s.detectedPlatform);
  const { setRaw: storeRaw, setCard, setDetectedPlatform } = useStore.getState();

  async function detect() {
    setBusy(true);
    setErr(null);
    storeRaw(raw);
    try {
      const r = await api.parse({ raw });
      setCard(r.card);
      setDetectedPlatform(r.detectedPlatform);
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'parse failed');
    } finally {
      setBusy(false);
    }
  }

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    setBusy(true);
    setErr(null);
    try {
      const r = await api.parseFile(f);
      setCard(r.card);
      setDetectedPlatform(r.detectedPlatform);
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : 'parse failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <textarea
        className="w-full min-h-32 border rounded p-3 font-mono text-sm"
        placeholder="Paste your character card text here (CAI / Chai / PolyBuzz)…"
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
      />
      <div className="flex gap-3 items-center">
        <button
          type="button"
          className="px-4 py-2 bg-slate-900 text-white rounded disabled:opacity-40"
          disabled={!raw.trim() || busy}
          onClick={detect}
        >
          {busy ? 'Detecting…' : 'Detect source'}
        </button>
        <label className="text-sm text-slate-600 cursor-pointer">
          or upload PNG / JSON
          <input
            type="file"
            className="hidden"
            accept=".png,.json"
            onChange={onFile}
          />
        </label>
        {detected && (
          <span className="text-sm">
            Detected: <b>{detected}</b>
          </span>
        )}
        {err && <span className="text-sm text-red-600">{err}</span>}
      </div>
    </div>
  );
}
