import { useStore } from '~/lib/store';
import type { Card } from '~/lib/types';

function toMarkdown(card: Card): string {
  const lines: string[] = [];
  for (const [k, v] of Object.entries(card)) {
    if (v == null || v === '') continue;
    lines.push(`## ${k}`, '', String(v), '');
  }
  return lines.join('\n');
}

function download(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

export default function ExportBar() {
  const finalFields = useStore((s) => s.finalFields());
  const has = Object.keys(finalFields).length > 0;

  async function copyAll() {
    const md = toMarkdown(finalFields);
    try { await navigator.clipboard.writeText(md); } catch { /* user falls back to download */ }
  }

  return (
    <div className="sticky bottom-0 inset-x-0 border-t bg-white/90 backdrop-blur px-6 py-3 flex flex-wrap gap-2 items-center">
      <button type="button" disabled={!has}
        onClick={copyAll}
        className="px-3 py-1 bg-slate-900 text-white rounded text-sm disabled:opacity-40">
        Copy all
      </button>
      <button type="button" disabled={!has}
        onClick={() => download('card.md', toMarkdown(finalFields), 'text/markdown')}
        className="px-3 py-1 border rounded text-sm disabled:opacity-40">
        Download .md
      </button>
      <button type="button" disabled={!has}
        onClick={() => download('card.json', JSON.stringify(finalFields, null, 2), 'application/json')}
        className="px-3 py-1 border rounded text-sm disabled:opacity-40">
        Download .json
      </button>
      <button type="button" disabled
        title="Coming October 2026"
        className="px-3 py-1 border rounded text-sm opacity-50 cursor-not-allowed">
        Tavern PNG
      </button>
    </div>
  );
}
