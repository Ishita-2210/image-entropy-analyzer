export const API = '/api/v1';
export async function api<T>(path: string, body?: unknown, method?: string): Promise<T> {
  const response = await fetch(API + path, {
    method: method ?? (body ? 'POST' : 'GET'),
    headers: body && !(body instanceof FormData) ? { 'Content-Type': 'application/json' } : {},
    body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.error?.message ?? `Request failed (${response.status}).`);
  }
  return response.json() as Promise<T>;
}
export const preview = (id: string, size = 1024) => `${API}/images/${id}/preview?size=${size}`;
export const fmt = (n: number | null | undefined, digits = 3) =>
  n == null
    ? '—'
    : n.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });
export const bytes = (n: number) =>
  n >= 1048576 ? `${fmt(n / 1048576, 2)} MB` : `${fmt(n / 1024, 1)} KB`;
export function downloadJSON(value: unknown, name: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }),
  );
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
