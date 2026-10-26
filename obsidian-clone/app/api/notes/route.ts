import { fail, handle, isResponse, json, parseBody } from '@/lib/http';
import { createNote, getVault } from '@/lib/notes';
import { noteCreate } from '@/lib/validation';

export const POST = (req: Request) =>
  handle(async () => {
    const body = await parseBody(req, noteCreate);
    if (isResponse(body)) return body;
    if (!getVault(body.vault)) return fail('Хранилище не найдено', 404);
    return json(createNote(body.vault, body.title, body.folder ?? null), 201);
  });
