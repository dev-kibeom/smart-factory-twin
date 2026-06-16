// src/app/layout.tsx
import './globals.css';

export const metadata = {
  title: 'Smart Factory Digital Twin',
  description: 'Sim-to-Real Multi-Agent Edge Control Console',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}