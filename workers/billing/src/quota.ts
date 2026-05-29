const FREE_CAP = 5;
const TTL_S = 60 * 60 * 26;

function dayKey(ip: string): string {
  const d = new Date().toISOString().slice(0, 10);
  return `quota:ai:${ip}:${d}`;
}

export async function readQuota(kv: KVNamespace, ip: string): Promise<{ aiUsed: number; aiCap: number; tier: 'free' }> {
  const used = parseInt((await kv.get(dayKey(ip))) ?? '0', 10);
  return { aiUsed: used, aiCap: FREE_CAP, tier: 'free' };
}

export async function bumpQuota(kv: KVNamespace, ip: string): Promise<number> {
  const k = dayKey(ip);
  const used = parseInt((await kv.get(k)) ?? '0', 10) + 1;
  await kv.put(k, String(used), { expirationTtl: TTL_S });
  return used;
}
