// Mirrors chara-convert/chara_convert/normalizer.py::NormalizedCard identity fields.
// Field names match Python dataclass keys exactly (snake_case).
export interface Card {
  name: string;
  description?: string;
  personality?: string;
  scenario?: string;
  first_mes?: string;
  mes_example?: string;
  creator?: string;
  tags?: string[];
  [k: string]: unknown;
}

export type FieldName = keyof Card | string;

export interface GapReport {
  ready_score: number;  // 0-100 scale (per chara_convert/diff.py)
  fields: Record<string, 'ok' | 'partial' | 'missing' | 'warn'>;
}

export interface PlatformEntry {
  slug: string;
  name: string;
  kind?: 'file' | 'paste';
}

export interface PlatformsResponse {
  sources: PlatformEntry[];
  targets: PlatformEntry[];
}

export interface AiSession {
  field: string;
  status: 'idle' | 'streaming' | 'done' | 'error';
  text: string;
}
