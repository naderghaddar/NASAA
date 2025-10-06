export const API = (p: string): string =>
  `${process.env.NEXT_PUBLIC_API_BASE ?? ""}${p}`;

// Single generic for the response; request body is just a safe record type
export async function postJSON<T>(
  url: string,
  body: Record<string, unknown>
): Promise<T> {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    throw new Error(text || `HTTP ${r.status}`);
  }
  return (await r.json()) as T;
}
