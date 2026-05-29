import { useBilling } from '~/lib/billing/client';
import { MIN_BALANCE_TO_TRY } from '~/lib/billing/constants';

// Replaces UpgradeCTA (tier-based) with a credit-balance-based banner.
// Renders only when the user is identified and below the try threshold —
// matches the same gate the AiAssistPanel button uses, so the CTA and
// the disabled button appear together.
export default function LowCreditCTA() {
  const { balance, loaded, userId } = useBilling();

  if (!loaded || userId === null) return null;
  if (balance >= MIN_BALANCE_TO_TRY) return null;

  const base = (import.meta.env.BASE_URL as string | undefined) ?? '/chara-convert/';

  return (
    <div className="bg-amber-100 border border-amber-300 rounded p-4 mt-4">
      <p className="font-medium">Low credit ({balance} credit left).</p>
      <a
        href={`${base}pricing`}
        className="text-amber-700 underline hover:text-amber-900 mt-2 inline-block"
      >
        Top-up your account
      </a>
    </div>
  );
}
