import { fail, handle, isResponse, json, parseBody } from '@/lib/http';
import { deleteNote, getNote, updateNote } from '@/lib/notes';
import { notePatch } from '@/lib/validation';

type Ctx = { params: Promise<{ id: string }> };

export const GET = (_: Request, { params }: Ctx) =>
  handle(async () => {
    const note = getNote((await params).id);
    return note ? json(note) : fail('Заметка не найдена', 404);
  });

export const PATCH = (req: Request, { params }: Ctx) =>
  handle(async () => {
    const body = await parseBody(req, notePatch);
    if (isResponse(body)) return body;
    const note = updateNote((await params).id, body);
    return note ? json(note) : fail('Заметка не найдена', 404);
  });

export const DELETE = (_: Request, { params }: Ctx) =>
  handle(async () => (deleteNote((await params).id) ? json({ ok: true }) : fail('Заметка не найдена', 404)));

/** sendBeacon при закрытии вкладки шлёт POST; логика та же, что у PATCH. */
export const POST = PATCH;
