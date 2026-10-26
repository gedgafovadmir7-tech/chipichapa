import { NextResponse } from 'next/server';
import { ZodError, type ZodType } from 'zod';

export const json = (data: unknown, status = 200) => NextResponse.json(data, { status });
export const fail = (message: string, status = 400) => NextResponse.json({ error: message }, { status });

export async function parseBody<T>(req: Request, schema: ZodType<T>): Promise<T | NextResponse> {
  try {
    return schema.parse(await req.json());
  } catch (e) {
    if (e instanceof ZodError) return fail(e.issues[0]?.message ?? 'Некорректные данные', 422);
    return fail('Некорректный JSON', 400);
  }
}

export const isResponse = (v: unknown): v is NextResponse => v instanceof NextResponse;

import { ConflictError } from './notes';

/** Превращает типичные ошибки БД и домена в понятные HTTP-ответы. */
export async function handle(fn: () => Promise<NextResponse> | NextResponse): Promise<NextResponse> {
  try {
    return await fn();
  } catch (e) {
    if (e instanceof ConflictError) return fail(e.message, 409);
    const code = (e as { code?: string }).code;
    if (code === 'SQLITE_CONSTRAINT_UNIQUE') return fail('Такое имя уже занято', 409);
    if (code?.startsWith('SQLITE_CONSTRAINT')) return fail('Нарушено ограничение данных', 422);
    console.error(e);
    return fail('Внутренняя ошибка', 500);
  }
}
