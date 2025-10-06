export const API = (p: string) => `${process.env.NEXT_PUBLIC_API_BASE}${p}`;

export async function postJSON<T, TBody extends Record<string, unknown>>(
  path: string,
  body: TBody,
  init?: RequestInit
): Promise<T> {
  const r = await fetch(API(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    ...init,
  });
  if (!r.ok) throw new Error(await r.text());
  return (await r.json()) as T;
}

// (Optional) GET helper if you need it
export async function getJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(API(path), init);
  if (!r.ok) throw new Error(await r.text());
  return (await r.json()) as T;
}
