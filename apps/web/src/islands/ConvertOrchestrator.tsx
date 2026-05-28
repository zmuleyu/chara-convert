import { useEffect } from 'react';
import { api } from '~/lib/api';
import { useStore } from '~/lib/store';

export default function ConvertOrchestrator() {
  const sourceCard = useStore((s) => s.sourceCard);
  const targetSlug = useStore((s) => s.targetSlug);
  const setConverted = useStore((s) => s.setConverted);
  const setGap = useStore((s) => s.setGap);

  useEffect(() => {
    if (!sourceCard || !targetSlug) return;
    let cancelled = false;
    api.convert({ card: sourceCard, targetSlug })
      .then((r) => { if (!cancelled) { setConverted(r.converted); setGap(r.gap); } })
      .catch((e) => { if (!cancelled) console.error('[ConvertOrchestrator] /api/convert failed:', e); });
    return () => { cancelled = true; };
  }, [sourceCard, targetSlug, setConverted, setGap]);

  return null;
}
