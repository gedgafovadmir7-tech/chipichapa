import { fail, handle, isResponse, json, parseBody } from '@/lib/http';
import { deleteFolder, updateFolder } from '@/lib/notes';
import { folderPatch } from '@/lib/validation';

type Ctx = { params: Promise<{ id: string }> };

export const PATCH = (req: Request, { params }: Ctx) =>
  handle(async () => {
    const body = await parseBody(req, folderPatch);
    if (isResponse(body)) return body;
    const folder = updateFolder((await params).id, body);
    return folder ? json(folder) : fail('Папка не найдена', 404);
  });

export const DELETE = (_: Request, { params }: Ctx) =>
  handle(async () => (deleteFolder((await params).id) ? json({ ok: true }) : fail('Папка не найдена', 404)));
