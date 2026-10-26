export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

export async function api<T>(path: string, init?: RequestInit & { json?: unknown }): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: init?.json !== undefined ? { 'content-type': 'application/json' } : undefined,
    body: init?.json !== undefined ? JSON.stringify(init.json) : init?.body,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError((data as { error?: string }).error ?? 'Ошибка запроса', res.status);
  return data as T;
}

export type TreeFolder = { id: string; parent_id: string | null; name: string };
export type TreeNote = { id: string; folder_id: string | null; title: string; updated_at: string };
export type Tree = { folders: TreeFolder[]; notes: TreeNote[] };
export type NoteFull = { id: string; vault_id: string; folder_id: string | null; title: string; content: string; updated_at: string };
