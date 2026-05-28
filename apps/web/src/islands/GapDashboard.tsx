import { useStore } from '~/lib/store';

const BUCKET_LABEL: Record<string, string> = {
  ok: 'Ready', partial: 'Partial', missing: 'Missing', warn: 'Warn',
};
const BUCKET_COLOR: Record<string, string> = {
  ok: 'bg-emerald-100 text-emerald-900',
  partial: 'bg-amber-100 text-amber-900',
  missing: 'bg-red-100 text-red-900',
  warn: 'bg-yellow-100 text-yellow-900',
};

export default function GapDashboard() {
  const gap = useStore((s) => s.gap);
  if (!gap) return <p className="text-sm text-slate-500">Run convert to see the gap report.</p>;
  const pct = Math.round(gap.ready_score);
  return (
    <div className="space-y-4">
      <div className="text-3xl font-bold">{pct}% ready</div>
      <ul className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {Object.entries(gap.fields).map(([field, bucket]) => (
          <li
            key={field}
            className={`px-3 py-2 rounded text-sm ${BUCKET_COLOR[bucket] ?? 'bg-slate-100'}`}
          >
            <a href={`#step=edit&field=${encodeURIComponent(field)}`} className="block">
              <div className="font-medium">{field}</div>
              <div className="text-xs">{BUCKET_LABEL[bucket] ?? bucket}</div>
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
