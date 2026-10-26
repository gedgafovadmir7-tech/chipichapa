import { fail, handle, isResponse, json, parseBody } from '@/lib/http';
import { createFolder, getVault } from '@/lib/notes';
import { folderCreate } from '@/lib/validation';

export const POST = (req: Request) =>
  handle(async () => {
    const body = await parseBody(req, folderCreate);
    if (isResponse(body)) return body;
    if (!getVault(body.vault)) return fail('Хранилище не найдено', 404);
    return json(createFolder(body.vault, body.name, body.parent ?? null), 201);
  });
