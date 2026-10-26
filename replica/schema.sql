-- SQLite. Тест для себя: один пользователь, без авторизации и RLS.
-- Время хранится как ISO-8601 строка в UTC.
PRAGMA foreign_keys = ON;

CREATE TABLE vault (
  id         TEXT PRIMARY KEY,              -- uuid, генерируется в коде
  name       TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE folder (
  id         TEXT PRIMARY KEY,
  vault_id   TEXT NOT NULL REFERENCES vault(id) ON DELETE CASCADE,
  parent_id  TEXT REFERENCES folder(id) ON DELETE CASCADE,
  name       TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX folder_vault_idx  ON folder(vault_id);
CREATE INDEX folder_parent_idx ON folder(parent_id);
-- уникальное имя папки внутри родителя (корень = '')
CREATE UNIQUE INDEX folder_unique_name ON folder(vault_id, COALESCE(parent_id,''), name);

CREATE TABLE note (
  id         TEXT PRIMARY KEY,
  vault_id   TEXT NOT NULL REFERENCES vault(id) ON DELETE CASCADE,
  folder_id  TEXT REFERENCES folder(id) ON DELETE SET NULL,
  title      TEXT NOT NULL,                 -- имя файла без .md
  title_key  TEXT NOT NULL,                 -- title в нижнем регистре (считается в коде; NOCASE не знает кириллицу)
  content    TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX note_vault_idx  ON note(vault_id);
CREATE INDEX note_folder_idx ON note(folder_id);
CREATE INDEX note_updated_idx ON note(vault_id, updated_at DESC);
-- Obsidian находит [[title]] без учёта регистра и без пути: имя уникально в vault
CREATE UNIQUE INDEX note_unique_title ON note(vault_id, title_key);

-- Производные данные, пересчитываются парсингом content при сохранении
CREATE TABLE link (
  id             TEXT PRIMARY KEY,
  from_note_id   TEXT NOT NULL REFERENCES note(id) ON DELETE CASCADE,
  to_note_id     TEXT REFERENCES note(id) ON DELETE SET NULL, -- NULL = ссылка на несуществующую
  target_text    TEXT NOT NULL,             -- как написано в [[...]]
  heading        TEXT,                      -- [[a#heading]]
  alias          TEXT,                      -- [[a|alias]]
  created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX link_from_idx ON link(from_note_id);
CREATE INDEX link_to_idx   ON link(to_note_id);
CREATE INDEX link_target_idx ON link(target_text);

CREATE TABLE tag (
  note_id TEXT NOT NULL REFERENCES note(id) ON DELETE CASCADE,
  name    TEXT NOT NULL,                    -- без '#', вложенные: a/b
  PRIMARY KEY (note_id, name)
);
CREATE INDEX tag_name_idx ON tag(name);

-- Полнотекстовый поиск (в т.ч. кириллица: tokenize unicode61)
CREATE VIRTUAL TABLE note_fts USING fts5(title, content, content='note', content_rowid='rowid', tokenize='unicode61 remove_diacritics 2');
CREATE TRIGGER note_ai AFTER INSERT ON note BEGIN
  INSERT INTO note_fts(rowid,title,content) VALUES (new.rowid,new.title,new.content);
END;
CREATE TRIGGER note_ad AFTER DELETE ON note BEGIN
  INSERT INTO note_fts(note_fts,rowid,title,content) VALUES('delete',old.rowid,old.title,old.content);
END;
CREATE TRIGGER note_au AFTER UPDATE ON note BEGIN
  INSERT INTO note_fts(note_fts,rowid,title,content) VALUES('delete',old.rowid,old.title,old.content);
  INSERT INTO note_fts(rowid,title,content) VALUES (new.rowid,new.title,new.content);
END;

CREATE TABLE setting (
  key   TEXT PRIMARY KEY,                   -- theme, ui_state и т.п.
  value TEXT NOT NULL
);
