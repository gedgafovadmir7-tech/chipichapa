import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = { title: 'Заметки', description: 'Личное хранилище заметок с вики-ссылками' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
