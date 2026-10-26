'use client';
import { useEffect, useRef, useState } from 'react';
import { api, ApiError, type NoteFull } from '@/lib/client';

type SaveState = 'saved' | 'saving' | 'dirty' | 'error' | 'conflict';
const labels: Record<SaveState, string> = {
  saved: 'Сохранено', saving: 'Сохранение…', dirty: 'Есть несохранённые изменения',
  error: 'Не удалось сохранить', conflict: 'Заметка изменена в другом окне',
};
const DEBOUNCE_MS = 800;

export function Editor({ noteId, onSaved }: { noteId: string; onSaved: (n: NoteFull) => void }) {
  const [note, setNote] = useState<NoteFull | null>(null);
  const [text, setText] = useState('');
  const [state, setState] = useState<SaveState>('saved');
  const [loadError, setLoadError] = useState('');
  const version = useRef('');
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const latest = useRef({ text: '', saving: false });

  useEffect(() => {
    let cancelled = false;
    setNote(null); setLoadError(''); setState('saved');
    api<NoteFull>(`/api/notes/${noteId}`)
      .then((n) => { if (cancelled) return; setNote(n); setText(n.content); version.current = n.updated_at; latest.current.text = n.content; })
      .catch((e: ApiError) => !cancelled && setLoadError(e.status === 404 ? 'Заметка не найдена. Возможно, её удалили.' : e.message));
    return () => { cancelled = true; clearTimeout(timer.current); };
  }, [noteId]);

  async function save() {
    if (latest.current.saving) { timer.current = setTimeout(save, 200); return; }
    latest.current.saving = true;
    const sending = latest.current.text;
    setState('saving');
    try {
      const n = await api<NoteFull>(`/api/notes/${noteId}`, { method: 'PATCH', json: { content: sending, baseUpdatedAt: version.current } });
      version.current = n.updated_at;
      setState(latest.current.text === sending ? 'saved' : 'dirty');
      onSaved(n);
    } catch (e) {
      setState(e instanceof ApiError && e.status === 409 ? 'conflict' : 'error');
    } finally { latest.current.saving = false; }
  }

  function change(v: string) {
    setText(v);
    latest.current.text = v;
    setState('dirty');
    clearTimeout(timer.current);
    timer.current = setTimeout(save, DEBOUNCE_MS);
  }

  // сохраняем при закрытии вкладки, если остались изменения
  useEffect(() => {
    const onHide = () => {
      if (!note || latest.current.text === note.content) return;
      navigator.sendBeacon?.(`/api/notes/${noteId}`, new Blob([JSON.stringify({ content: latest.current.text })], { type: 'application/json' }));
    };
    window.addEventListener('pagehide', onHide);
    return () => window.removeEventListener('pagehide', onHide);
  }, [note, noteId]);

  if (loadError) return <p role="alert" className="p-6 text-danger">{loadError}</p>;
  if (!note) return <p className="p-6 text-muted">Загрузка…</p>;

  return (
    <div className="mx-auto flex h-full w-full max-w-[760px] flex-col px-4 py-4">
      <h1 className="mb-2 text-2xl font-bold break-words">{note.title}</h1>
      <textarea
        aria-label={`Текст заметки «${note.title}»`}
        value={text}
        onChange={(e) => change(e.target.value)}
        placeholder="Начните писать…"
        spellCheck={false}
        className="min-h-0 flex-1 resize-none rounded-md bg-bg p-2 font-mono text-sm leading-relaxed text-text"
      />
      <p role="status" className={`pt-2 text-xs ${state === 'error' || state === 'conflict' ? 'text-danger' : 'text-muted'}`}>
        {labels[state]}
        {state === 'error' && <button type="button" onClick={save} className="ml-2 underline">Повторить</button>}
      </p>
    </div>
  );
}
