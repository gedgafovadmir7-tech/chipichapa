import { z } from 'zod';

// Символы, недопустимые в именах файлов
const forbidden = /[\\/:*?"<>|#^\[\]]/;
export const nameSchema = z
  .string()
  .trim()
  .min(1, 'Введите имя')
  .max(200, 'Слишком длинное имя')
  .refine((s) => !forbidden.test(s), 'Имя содержит недопустимые символы');

export const MAX_CONTENT = 2_000_000;
export const contentSchema = z.string().max(MAX_CONTENT, 'Заметка слишком большая');

export const vaultCreate = z.object({ name: nameSchema });
export const noteCreate = z.object({ vault: z.string().uuid(), title: nameSchema.optional(), folder: z.string().uuid().nullable().optional() });
export const notePatch = z.object({ title: nameSchema.optional(), content: contentSchema.optional(), folder: z.string().uuid().nullable().optional(), baseUpdatedAt: z.string().optional() });
export const folderCreate = z.object({ vault: z.string().uuid(), name: nameSchema, parent: z.string().uuid().nullable().optional() });
export const folderPatch = z.object({ name: nameSchema.optional(), parent: z.string().uuid().nullable().optional() });
