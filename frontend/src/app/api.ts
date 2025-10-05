export const API = (p: string) => `${process.env.NEXT_PUBLIC_API_BASE}${p}`;
export async function postJSON<T>(url: string, body: any): Promise<T> {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type":"application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<T>;
}
