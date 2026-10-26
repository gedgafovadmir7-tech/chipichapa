import { getDb, newId, titleKey } from './db';

export type Note = { id: string; vault_id: string; folder_id: string | null; title: string; content: string; created_at: string; updated_at: string };
export type Folder = { id: string; vault_id: string; parent_id: string | null; name: string };

export class ConflictError extends Error {}

export function listVaults() {
  return getDb().prepare('select id, name, created_at from vault order by created_at').all();
}

export function createVault(name: string) {
  const id = newId();
  getDb().prepare('insert into vault (id, name) values (?, ?)').run(id, name);
  return getDb().prepare('select * from vault where id = ?').get(id);
}

export function getVault(id: string) {
  return getDb().prepare('select * from vault where id = ?').get(id) as { id: string; name: string } | undefined;
}

export function getTree(vaultId: string) {
  const db = getDb();
  const folders = db.prepare('select id, parent_id, name from folder where vault_id = ? order by name').all(vaultId);
  const notes = db.prepare('select id, folder_id, title, updated_at from note where vault_id = ? order by title').all(vaultId);
  return { folders, notes };
}

export function getNote(id: string) {
  return getDb().prepare('select * from note where id = ?').get(id) as Note | undefined;
}

function uniqueTitle(vaultId: string, base: string) {
  const db = getDb();
  const taken = (t: string) => db.prepare('select 1 from note where vault_id = ? and title_key = ?').get(vaultId, titleKey(t));
  if (!taken(base)) return base;
  for (let i = 1; ; i++) {
    const candidate = `${base} ${i}`;
    if (!taken(candidate)) return candidate;
  }
}

export function createNote(vaultId: string, title: string | undefined, folderId: string | null) {
  const id = newId();
  const finalTitle = uniqueTitle(vaultId, title ?? 'Без названия');
  getDb()
    .prepare('insert into note (id, vault_id, folder_id, title, title_key) values (?, ?, ?, ?, ?)')
    .run(id, vaultId, folderId, finalTitle, titleKey(finalTitle));
  return getNote(id)!;
}

export function updateNote(id: string, patch: { title?: string; content?: string; folder?: string | null; baseUpdatedAt?: string }) {
  const db = getDb();
  const cur = getNote(id);
  if (!cur) return undefined;
  if (patch.baseUpdatedAt && patch.baseUpdatedAt !== cur.updated_at) throw new ConflictError('Заметка изменена в другом окне');
  const title = patch.title ?? cur.title;
  if (patch.title && titleKey(patch.title)) {
    const clash = db.prepare('select id from note where vault_id = ? and title_key = ? and id != ?').get(cur.vault_id, titleKey(title), id);
    if (clash) throw new ConflictError('Заметка с таким именем уже есть');
  }
  db.prepare(
    `update note set title = ?, title_key = ?, content = ?, folder_id = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') where id = ?`,
  ).run(title, titleKey(title), patch.content ?? cur.content, patch.folder === undefined ? cur.folder_id : patch.folder, id);
  return getNote(id)!;
}

export function deleteNote(id: string) {
  return getDb().prepare('delete from note where id = ?').run(id).changes > 0;
}

export function createFolder(vaultId: string, name: string, parent: string | null) {
  const id = newId();
  getDb().prepare('insert into folder (id, vault_id, parent_id, name) values (?, ?, ?, ?)').run(id, vaultId, parent, name);
  return getDb().prepare('select id, vault_id, parent_id, name from folder where id = ?').get(id) as Folder;
}

export function updateFolder(id: string, patch: { name?: string; parent?: string | null }) {
  const db = getDb();
  const cur = db.prepare('select * from folder where id = ?').get(id) as Folder | undefined;
  if (!cur) return undefined;
  const parent = patch.parent === undefined ? cur.parent_id : patch.parent;
  // нельзя переместить папку внутрь самой себя или своего потомка
  for (let p = parent; p; p = (db.prepare('select parent_id from folder where id = ?').get(p) as { parent_id: string | null } | undefined)?.parent_id ?? null) {
    if (p === id) throw new ConflictError('Нельзя переместить папку внутрь себя');
  }
  db.prepare(`update folder set name = ?, parent_id = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') where id = ?`).run(patch.name ?? cur.name, parent, id);
  return db.prepare('select id, vault_id, parent_id, name from folder where id = ?').get(id) as Folder;
}

export function deleteFolder(id: string) {
  return getDb().prepare('delete from folder where id = ?').run(id).changes > 0;
}
