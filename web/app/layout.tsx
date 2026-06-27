import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Datazos RM — ofertas de distribuidoras y supermercados',
  description: 'Los mejores precios de distribuidoras, almacenes y supermercados de la Región Metropolitana.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <header className="topbar">
          <h1>🔥 Datazos RM</h1>
          <span className="tagline">Ofertas de distribuidoras y supermercados</span>
        </header>
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
