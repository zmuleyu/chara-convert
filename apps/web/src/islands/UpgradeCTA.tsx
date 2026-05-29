import { useBilling } from '~/lib/billing/client';

export default function UpgradeCTA() {
  const { tier, aiUsed, aiCap } = useBilling();

  // Show banner only when free tier AND quota is exhausted
  if (tier !== 'free' || aiCap < 0 || aiUsed < aiCap) {
    return null;
  }

  const base = (import.meta.env.BASE_URL as string | undefined) ?? '/chara-convert/';

  return (
    <div className="bg-amber-100 border border-amber-300 rounded p-4 mt-4">
      <p className="font-medium">
        Daily free AI quota reached ({aiUsed}/{aiCap}).
      </p>
      <a
        href={`${base}pricing`}
        className="text-amber-700 underline hover:text-amber-900 mt-2 inline-block"
      >
        Upgrade to Creator — $9/mo
      </a>
    </div>
  );
}
