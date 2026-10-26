'use client';
import { useEffect, useRef, useState } from 'react';
import { Button, TextInput } from './ui';

type Base = { title: string; onClose: () => void; children: React.ReactNode };

/** Нативный <dialog>: ловушка фокуса и Esc из коробки. */
function Modal({ title, onClose, children }: Base) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { ref.current?.showModal(); }, []);
  return (
    <dialog ref={ref} onClose={onClose} aria-labelledby="dlg-title" className="w-[min(92vw,26rem)] rounded-lg border border-border bg-bg p-5 text-text shadow-modal backdrop:bg-black/40">
      <h2 id="dlg-title" className="mb-4 text-lg font-bold">{title}</h2>
      {children}
    </dialog>
  );
}

export function NameDialog({ title, label, initial = '', submitLabel, onSubmit, onClose }: {
  title: string; label: string; initial?: string; submitLabel: string;
  onSubmit: (value: string) => Promise<void>; onClose: () => void;
}) {
  const [value, setValue] = useState(initial);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try { await onSubmit(value.trim()); onClose(); } catch (err) { setError((err as Error).message); } finally { setBusy(false); }
  }
  return (
    <Modal title={title} onClose={onClose}>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <TextInput label={label} value={value} onChange={(e) => setValue(e.target.value)} error={error} autoFocus onFocus={(e) => e.target.select()} />
        <div className="flex justify-end gap-2">
          <Button onClick={onClose}>Отмена</Button>
          <Button type="submit" variant="primary" loading={busy} disabled={!value.trim()}>{submitLabel}</Button>
        </div>
      </form>
    </Modal>
  );
}

export function ConfirmDialog({ title, text, confirmLabel, onConfirm, onClose }: {
  title: string; text: string; confirmLabel: string; onConfirm: () => Promise<void>; onClose: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function go() {
    setBusy(true);
    try { await onConfirm(); onClose(); } catch (err) { setError((err as Error).message); setBusy(false); }
  }
  return (
    <Modal title={title} onClose={onClose}>
      <p className="mb-4 text-muted">{text}</p>
      {error && <p role="alert" className="mb-3 text-sm text-danger">{error}</p>}
      <div className="flex justify-end gap-2">
        <Button onClick={onClose} autoFocus>Отмена</Button>
        <Button variant="danger" loading={busy} onClick={go}>{confirmLabel}</Button>
      </div>
    </Modal>
  );
}
