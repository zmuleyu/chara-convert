import { useStore } from '~/lib/store';

interface Props {
  label: string;
  sampleUrl: string;
  detectedPlatform: string;
}

const BASE_URL = (import.meta.env.BASE_URL as string | undefined) ?? '/chara-convert/';

export default function SampleButton({ label, sampleUrl, detectedPlatform }: Props) {
  async function load() {
    const res = await fetch(sampleUrl);
    if (!res.ok) return;
    const raw = await res.text();
    useStore.getState().setRaw(raw);
    useStore.getState().setDetectedPlatform(detectedPlatform);
    window.location.href = `${BASE_URL}convert#step=source`;
  }
  return (
    <button
      type="button"
      onClick={load}
      className="px-3 py-2 text-sm border rounded hover:bg-slate-50"
    >
      Try {label}
    </button>
  );
}
