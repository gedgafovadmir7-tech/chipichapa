'use client';
import { useState } from 'react';
import { ChevronDown, ChevronRight, FileText, Folder, FolderPlus, FilePlus, Pencil, Trash2 } from 'lucide-react';
import { IconButton } from './ui';
import type { Tree } from '@/lib/client';

type Props = {
  tree: Tree;
  activeId: string | null;
  onOpen: (id: string) => void;
  onCreateNote: (folderId: string | null) => void;
  onCreateFolder: (parentId: string | null) => void;
  onRenameNote: (id: string, current: string) => void;
  onRenameFolder: (id: string, current: string) => void;
  onDeleteNote: (id: string, title: string) => void;
  onDeleteFolder: (id: string, name: string) => void;
};

export function FileTree(p: Props) {
  const [closed, setClosed] = useState<Set<string>>(new Set());
  const toggle = (id: string) => setClosed((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });

  const renderLevel = (parent: string | null, depth: number): React.ReactNode => (
    <>
      {p.tree.folders.filter((f) => f.parent_id === parent).map((f) => {
        const isClosed = closed.has(f.id);
        return (
          <li key={f.id} role="none">
            <div role="treeitem" aria-expanded={!isClosed} aria-selected={false} className="group flex items-center gap-1 rounded-md pr-1 hover:bg-surface-2" style={{ paddingLeft: depth * 12 }}>
              <button type="button" onClick={() => toggle(f.id)} className="flex min-w-0 flex-1 items-center gap-1 px-1 py-1 text-left text-sm">
                {isClosed ? <ChevronRight size={14} aria-hidden /> : <ChevronDown size={14} aria-hidden />}
                <Folder size={14} aria-hidden className="shrink-0 text-muted" />
                <span className="truncate">{f.name}</span>
              </button>
              <span className="flex opacity-0 group-hover:opacity-100 group-focus-within:opacity-100">
                <IconButton label={`Новая заметка в «${f.name}»`} onClick={() => p.onCreateNote(f.id)}><FilePlus size={14} /></IconButton>
                <IconButton label={`Новая папка в «${f.name}»`} onClick={() => p.onCreateFolder(f.id)}><FolderPlus size={14} /></IconButton>
                <IconButton label={`Переименовать папку «${f.name}»`} onClick={() => p.onRenameFolder(f.id, f.name)}><Pencil size={14} /></IconButton>
                <IconButton label={`Удалить папку «${f.name}»`} onClick={() => p.onDeleteFolder(f.id, f.name)}><Trash2 size={14} /></IconButton>
              </span>
            </div>
            {!isClosed && <ul role="group">{renderLevel(f.id, depth + 1)}</ul>}
          </li>
        );
      })}
      {p.tree.notes.filter((n) => n.folder_id === parent).map((n) => (
        <li key={n.id} role="none">
          <div role="treeitem" aria-selected={n.id === p.activeId} className={`group flex items-center gap-1 rounded-md pr-1 ${n.id === p.activeId ? 'bg-surface-2' : 'hover:bg-surface-2'}`} style={{ paddingLeft: depth * 12 + 18 }}>
            <button type="button" onClick={() => p.onOpen(n.id)} aria-current={n.id === p.activeId ? 'page' : undefined} className="flex min-w-0 flex-1 items-center gap-1 px-1 py-1 text-left text-sm">
              <FileText size={14} aria-hidden className="shrink-0 text-muted" />
              <span className="truncate">{n.title}</span>
            </button>
            <span className="flex opacity-0 group-hover:opacity-100 group-focus-within:opacity-100">
              <IconButton label={`Переименовать «${n.title}»`} onClick={() => p.onRenameNote(n.id, n.title)}><Pencil size={14} /></IconButton>
              <IconButton label={`Удалить «${n.title}»`} onClick={() => p.onDeleteNote(n.id, n.title)}><Trash2 size={14} /></IconButton>
            </span>
          </div>
        </li>
      ))}
    </>
  );

  const empty = p.tree.folders.length === 0 && p.tree.notes.length === 0;
  return (
    <nav aria-label="Файлы" className="flex h-full flex-col">
      <div className="flex items-center justify-end border-b border-border px-1 py-1">
        <IconButton label="Новая заметка" onClick={() => p.onCreateNote(null)}><FilePlus size={16} /></IconButton>
        <IconButton label="Новая папка" onClick={() => p.onCreateFolder(null)}><FolderPlus size={16} /></IconButton>
      </div>
      {empty ? (
        <p className="p-4 text-sm text-muted">Пока нет заметок. Нажмите «Новая заметка» выше.</p>
      ) : (
        <ul role="tree" aria-label="Дерево файлов" className="flex-1 overflow-auto p-1">{renderLevel(null, 0)}</ul>
      )}
    </nav>
  );
}
