import Database from 'better-sqlite3';
import { mkdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

let db: Database.Database | undefined;

export function getDb(): Database.Database {
  if (db) return db;
  const dir = process.env.DATA_DIR ?? join(process.cwd(), 'data');
  mkdirSync(dir, { recursive: true });
  db = new Database(process.env.DB_FILE ?? join(dir, 'app.db'));
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');
  const hasSchema = db.prepare("select 1 from sqlite_master where name = 'vault'").get();
  if (!hasSchema) db.exec(readFileSync(join(process.cwd(), 'lib', 'schema.sql'), 'utf8'));
  return db;
}

export const newId = () => crypto.randomUUID();
export const titleKey = (title: string) => title.trim().toLocaleLowerCase('ru');
