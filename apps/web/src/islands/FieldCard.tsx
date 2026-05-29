import { useState } from 'react';
import { useStore } from '~/lib/store';
import AiAssistPanel from './AiAssistPanel';

interface Props { field: string }

export default function FieldCard({ field }: Props) {
  const value = useStore((s) => {
    const merged = { ...(s.converted ?? {}), ...s.overrides };
    return (merged[field] as string | undefined) ?? '';
  });
  const setOverride = useStore((s) => s.setOverride);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [aiOpen, setAiOpen] = useState(false);

  function save() {
    setOverride(field, draft);
    setEditing(false);
  }

  async function copy() {
    try { await navigator.clipboard.writeText(value); } catch { /* surfaced by ExportBar fallback */ }
  }

  return (
    <article className="border rounded p-4 space-y-2 group" data-field={field}>
      <header className="flex items-center justify-between">
        <h3 className="font-medium capitalize">{field.replace(/_/g, ' ')}</h3>
        <div className="opacity-0 group-hover:opacity-100 flex gap-2">
          <button type="button" className="text-xs underline" onClick={copy}>Copy</button>
          <button type="button" className="text-xs underline" onClick={() => setAiOpen(true)}>AI</button>
          {!editing && (
            <button type="button" className="text-xs underline" onClick={() => { setDraft(value); setEditing(true); }}>
              Edit
            </button>
          )}
        </div>
      </header>
      {editing ? (
        <>
          <textarea
            className="w-full min-h-24 border rounded p-2 text-sm"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
          <div className="flex gap-2 text-xs">
            <button type="button" className="px-2 py-1 bg-slate-900 text-white rounded" onClick={save}>Save</button>
            <button type="button" className="px-2 py-1 border rounded" onClick={() => setEditing(false)}>Cancel</button>
          </div>
        </>
      ) : (
        <p className="text-sm whitespace-pre-wrap text-slate-700">{value || <i className="text-slate-400">(empty)</i>}</p>
      )}
      {aiOpen && (
        <AiAssistPanel field={field} onClose={() => setAiOpen(false)} />
      )}
    </article>
  );
}
