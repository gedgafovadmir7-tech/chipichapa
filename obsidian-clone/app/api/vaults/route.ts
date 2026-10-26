import { handle, isResponse, json, parseBody } from '@/lib/http';
import { createVault, listVaults } from '@/lib/notes';
import { vaultCreate } from '@/lib/validation';

export const GET = () => handle(() => json(listVaults()));

export const POST = (req: Request) =>
  handle(async () => {
    const body = await parseBody(req, vaultCreate);
    if (isResponse(body)) return body;
    return json(createVault(body.name), 201);
  });
