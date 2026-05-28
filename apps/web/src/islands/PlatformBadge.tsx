import { useEffect, useState } from 'react';
import { api } from '~/lib/api';
import { useStore } from '~/lib/store';
import type { PlatformEntry } from '~/lib/types';

export default function PlatformBadge() {
  const [targets, setTargets] = useState<PlatformEntry[]>([]);
  const detected = useStore((s) => s.detectedPlatform);
  const targetSlug = useStore((s) => s.targetSlug);
  const setTarget = useStore((s) => s.setTarget);

  useEffect(() => {
    api.platforms()
      .then((p) => setTargets(p.targets))
      .catch(() => setTargets([]));
  }, []);

  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="px-3 py-1 bg-slate-100 rounded">{detected ?? '— source —'}</span>
      <span>→</span>
      <select
        className="border rounded px-2 py-1"
        value={targetSlug}
        onChange={(e) => setTarget(e.target.value)}
      >
        {targets.map((t) => (
          <option key={t.slug} value={t.slug}>{t.name}</option>
        ))}
      </select>
    </div>
  );
}
