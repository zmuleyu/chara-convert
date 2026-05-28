import type { Card } from './types';

const DB = 'chara-convert';
const STORE = 'cards';

interface SavedCard {
  id: string;
  raw: string | null;
  parsed: Card | null;
  target: string;
  overrides: Record<string, string>;
  updatedAt: number;
}

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE, { keyPath: 'id' });
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function saveCard(c: SavedCard): Promise<void> {
  const db = await open();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite');
    tx.objectStore(STORE).put(c);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function loadRecent(limit = 5): Promise<SavedCard[]> {
  const db = await open();
  return new Promise<SavedCard[]>((resolve, reject) => {
    const tx = db.transaction(STORE, 'readonly');
    const req = tx.objectStore(STORE).getAll();
    req.onsuccess = () => {
      const sorted = (req.result as SavedCard[]).sort((a, b) => b.updatedAt - a.updatedAt);
      resolve(sorted.slice(0, limit));
    };
    req.onerror = () => reject(req.error);
  });
}
