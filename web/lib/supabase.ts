import { createClient } from '@supabase/supabase-js';

// Cliente de solo lectura para el catálogo público (anon key + RLS).
export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export type Datazo = {
  id: string;
  producto: string;
  precio_dazo: number;
  precio_supermercado: number | null;
  ahorro_porcentaje: number | null;
  local: string | null;
  ubicacion_mencionada: string | null;
  direccion: string | null;
  telefono: string | null;
  horario: string | null;
  maps_url: string | null;
  foto_producto_url: string | null;
  fecha_encontrado: string | null;
};

export function clp(n: number | null): string {
  if (n == null) return '';
  return '$' + Math.round(n).toLocaleString('es-CL');
}
