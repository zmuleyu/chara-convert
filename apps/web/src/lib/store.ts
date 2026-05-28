import { create } from 'zustand';
import type { Card, FieldName, GapReport, AiSession } from './types';

interface State {
  sourceRaw: string | null;
  sourceCard: Card | null;
  detectedPlatform: string | null;
  targetSlug: string;
  converted: Card | null;
  gap: GapReport | null;
  overrides: Record<FieldName, string>;
  aiSession: AiSession | null;
  setRaw: (r: string | null) => void;
  setCard: (c: Card | null) => void;
  setDetectedPlatform: (p: string | null) => void;
  setTarget: (t: string) => void;
  setConverted: (c: Card | null) => void;
  setGap: (g: GapReport | null) => void;
  setOverride: (field: FieldName, value: string) => void;
  setAiSession: (s: AiSession | null) => void;
  finalFields: () => Card;
  reset: () => void;
}

const initial = {
  sourceRaw: null,
  sourceCard: null,
  detectedPlatform: null,
  targetSlug: 'fictionlab',
  converted: null,
  gap: null,
  overrides: {} as Record<FieldName, string>,
  aiSession: null,
} as const;

export const useStore = create<State>((set, get) => ({
  ...initial,
  setRaw: (r) => set({ sourceRaw: r }),
  setCard: (c) => set({ sourceCard: c, overrides: {} }),
  setDetectedPlatform: (p) => set({ detectedPlatform: p }),
  setTarget: (t) => set({ targetSlug: t, converted: null, gap: null }),
  setConverted: (c) => set({ converted: c }),
  setGap: (g) => set({ gap: g }),
  setOverride: (field, value) =>
    set((s) => ({ overrides: { ...s.overrides, [field]: value } })),
  setAiSession: (s) => set({ aiSession: s }),
  finalFields: () => ({ ...(get().converted ?? {}), ...get().overrides }) as Card,
  reset: () => set({ ...initial }),
}));
