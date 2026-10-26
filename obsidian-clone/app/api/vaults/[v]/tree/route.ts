import { fail, handle, json } from '@/lib/http';
import { getTree, getVault } from '@/lib/notes';

export const GET = (_: Request, { params }: { params: Promise<{ v: string }> }) =>
  handle(async () => {
    const { v } = await params;
    if (!getVault(v)) return fail('Хранилище не найдено', 404);
    return json(getTree(v));
  });
