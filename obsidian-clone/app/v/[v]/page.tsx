'use client';
import { use, useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { PanelLeft } from 'lucide-react';
import { FileTree } from '@/components/FileTree';
import { Editor } from '@/components/Editor';
import { ConfirmDialog, NameDialog } from '@/components/Dialogs';
import { IconButton } from '@/components/ui';
import { api, type NoteFull, type Tree } from '@/lib/client';

type Dialog =
  | { kind: 'newNote'; folder: string | null }
  | { kind: 'newFolder'; parent: string | null }
  | { kind: 'renameNote'; id: string; current: string }
  | { kind: 'renameFolder'; id: string; current: string }
  | { kind: 'deleteNote'; id: string; title: string }
  | { kind: 'deleteFolder'; id: string; name: string }
  | null;

export default function Workspace({ params }: { params: Promise<{ v: string }> }) {
  const { v } = use(params);
  const router = useRouter();
  const search = useSearchParams();
  const activeId = search.get('note');
  const [tree, setTree] = useState<Tree | null>(null);
  const [error, setError] = useState('');
  const [dialog, setDialog] = useState<Dialog>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const reload = useCallback(async () => {
    try { setTree(await api<Tree>(`/api/vaults/${v}/tree`)); setError(''); } catch (e) { setError((e as Error).message); }
  }, [v]);
  useEffect(() => { reload(); }, [reload]);

  const open = (id: string | null) => {
    router.push(id ? `/v/${v}?note=${id}` : `/v/${v}`);
    setSidebarOpen(false);
  };

  const close = () => setDialog(null);

  if (error) {
    return (
      <main className="p-6">
        <p role="alert" className="mb-4 text-danger">{error}</p>
        <Link href="/" className="underline">К списку хранилищ</Link>
      </main>
    );
  }

  return (
    <div className="flex h-dvh flex-col">
      <header className="flex h-10 shrink-0 items-center gap-2 border-b border-border bg-surface px-2">
        <IconButton label="Показать или скрыть файлы" aria-expanded={sidebarOpen} className="md:hidden" onClick={() => setSidebarOpen((s) => !s)}><PanelLeft size={16} /></IconButton>
        <Link href="/" className="text-sm text-muted hover:text-text">Хранилища</Link>
      </header>
      <div className="relative flex min-h-0 flex-1">
        <aside className={`${sidebarOpen ? 'absolute inset-y-0 left-0 z-10 flex' : 'hidden'} w-[260px] shrink-0 border-r border-border bg-surface md:static md:flex`}>
          {tree ? (
            <div className="w-full">
              <FileTree
                tree={tree}
                activeId={activeId}
                onOpen={open}
                onCreateNote={(folder) => setDialog({ kind: 'newNote', folder })}
                onCreateFolder={(parent) => setDialog({ kind: 'newFolder', parent })}
                onRenameNote={(id, current) => setDialog({ kind: 'renameNote', id, current })}
                onRenameFolder={(id, current) => setDialog({ kind: 'renameFolder', id, current })}
                onDeleteNote={(id, title) => setDialog({ kind: 'deleteNote', id, title })}
                onDeleteFolder={(id, name) => setDialog({ kind: 'deleteFolder', id, name })}
              />
            </div>
          ) : (
            <p className="p-4 text-sm text-muted">Загрузка…</p>
          )}
        </aside>
        <main className="min-w-0 flex-1 overflow-auto">
          {activeId ? (
            <Editor key={activeId} noteId={activeId} onSaved={(n: NoteFull) => setTree((t) => t && { ...t, notes: t.notes.map((x) => (x.id === n.id ? { ...x, updated_at: n.updated_at } : x)) })} />
          ) : (
            <p className="p-6 text-muted">Выберите заметку слева или создайте новую.</p>
          )}
        </main>
      </div>

      {dialog?.kind === 'newNote' && (
        <NameDialog title="Новая заметка" label="Название" submitLabel="Создать" onClose={close}
          onSubmit={async (title) => { const n = await api<NoteFull>('/api/notes', { method: 'POST', json: { vault: v, title, folder: dialog.folder } }); await reload(); open(n.id); }} />
      )}
      {dialog?.kind === 'newFolder' && (
        <NameDialog title="Новая папка" label="Название" submitLabel="Создать" onClose={close}
          onSubmit={async (name) => { await api('/api/folders', { method: 'POST', json: { vault: v, name, parent: dialog.parent } }); await reload(); }} />
      )}
      {dialog?.kind === 'renameNote' && (
        <NameDialog title="Переименовать заметку" label="Название" initial={dialog.current} submitLabel="Сохранить" onClose={close}
          onSubmit={async (title) => { await api(`/api/notes/${dialog.id}`, { method: 'PATCH', json: { title } }); await reload(); }} />
      )}
      {dialog?.kind === 'renameFolder' && (
        <NameDialog title="Переименовать папку" label="Название" initial={dialog.current} submitLabel="Сохранить" onClose={close}
          onSubmit={async (name) => { await api(`/api/folders/${dialog.id}`, { method: 'PATCH', json: { name } }); await reload(); }} />
      )}
      {dialog?.kind === 'deleteNote' && (
        <ConfirmDialog title="Удалить заметку?" text={`«${dialog.title}» будет удалена без возможности восстановления.`} confirmLabel="Удалить" onClose={close}
          onConfirm={async () => { await api(`/api/notes/${dialog.id}`, { method: 'DELETE' }); if (activeId === dialog.id) open(null); await reload(); }} />
      )}
      {dialog?.kind === 'deleteFolder' && (
        <ConfirmDialog title="Удалить папку?" text={`Папка «${dialog.name}» и вложенные папки будут удалены. Заметки из них переедут в корень хранилища.`} confirmLabel="Удалить" onClose={close}
          onConfirm={async () => { await api(`/api/folders/${dialog.id}`, { method: 'DELETE' }); await reload(); }} />
      )}
    </div>
  );
}
