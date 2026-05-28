import { useStore } from '~/lib/store';

const STEPS = [
  { id: 'source', label: 'Source', anchor: 'step-source' },
  { id: 'gap', label: 'Gap', anchor: 'step-gap' },
  { id: 'convert', label: 'Convert', anchor: 'step-convert' },
  { id: 'edit', label: 'Edit', anchor: 'step-edit' },
  { id: 'export', label: 'Export', anchor: 'step-export' },
] as const;

export default function StepperRail() {
  const s = useStore();
  const status = (id: typeof STEPS[number]['id']): 'done' | 'active' | 'todo' => {
    if (id === 'source') return s.sourceCard ? 'done' : 'active';
    if (id === 'gap') return s.gap ? 'done' : s.sourceCard ? 'active' : 'todo';
    if (id === 'convert') return s.converted ? 'done' : s.gap ? 'active' : 'todo';
    if (id === 'edit') return Object.keys(s.overrides).length > 0 ? 'done' : s.converted ? 'active' : 'todo';
    return s.converted ? 'active' : 'todo';
  };
  const glyph = (st: string) => (st === 'done' ? '✓' : st === 'active' ? '➤' : '○');
  return (
    <ol className="space-y-2 text-sm sticky top-6">
      {STEPS.map((step) => {
        const st = status(step.id);
        return (
          <li key={step.id} data-status={st} className={st === 'done' ? 'text-emerald-700' : st === 'active' ? 'text-slate-900 font-medium' : 'text-slate-400'}>
            <a href={`#${step.anchor}`}>{glyph(st)} {step.label}</a>
          </li>
        );
      })}
    </ol>
  );
}
