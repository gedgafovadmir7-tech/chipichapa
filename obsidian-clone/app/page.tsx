'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Button, TextInput } from '@/components/ui';
import { api } from '@/lib/client';

type Vault = { id: string; name: string };

export default function VaultsPage() {
  const [vaults, setVaults] = useState<Vault[] | null>(null);
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loadError, setLoadError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Vault[]>('/api/vaults').then(setVaults).catch((e) => setLoadError(e.message));
  }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const v = await api<Vault>('/api/vaults', { method: 'POST', json: { name } });
      setVaults((cur) => [...(cur ?? []), v]);
      setName('');
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-lg p-4 pt-12">
      <h1 className="mb-6 text-2xl font-bold">Хранилища</h1>
      {loadError && <p role="alert" className="mb-4 text-danger">{loadError}</p>}
      {vaults === null && !loadError && <p className="text-muted">Загрузка…</p>}
      {vaults?.length === 0 && <p className="mb-6 text-muted">Хранилищ пока нет. Создайте первое: в нём будут жить ваши заметки.</p>}
      <ul className="mb-8 flex flex-col gap-2">
        {vaults?.map((v) => (
          <li key={v.id}>
            <Link href={`/v/${v.id}`} className="block rounded-md border border-border bg-surface px-4 py-3 hover:bg-surface-2">{v.name}</Link>
          </li>
        ))}
      </ul>
      <form onSubmit={create} className="flex items-end gap-2">
        <div className="flex-1"><TextInput label="Название нового хранилища" value={name} onChange={(e) => setName(e.target.value)} error={error} /></div>
        <Button type="submit" variant="primary" loading={busy} disabled={!name.trim()}>Создать</Button>
      </form>
    </main>
  );
}
