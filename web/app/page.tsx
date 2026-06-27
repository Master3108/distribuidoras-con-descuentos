import { supabase, Datazo } from '../lib/supabase';
import DatazoCard from '../components/DatazoCard';
import Filtros from '../components/Filtros';

export const dynamic = 'force-dynamic'; // siempre datos frescos

export default async function Home({
  searchParams,
}: {
  searchParams: { q?: string; comuna?: string };
}) {
  const q = searchParams.q ?? '';
  const comuna = searchParams.comuna ?? '';

  let query = supabase
    .from('datazos')
    .select('*')
    .in('estado', ['publicado', 'pendiente'])
    .order('fecha_encontrado', { ascending: false })
    .limit(60);

  if (q) query = query.ilike('producto', `%${q}%`);
  if (comuna) query = query.ilike('ubicacion_mencionada', `%${comuna}%`);

  const { data, error } = await query;
  const datazos = (data ?? []) as Datazo[];

  return (
    <>
      <Filtros q={q} comuna={comuna} />
      {error ? (
        <p className="vacio">No se pudieron cargar los datazos.</p>
      ) : datazos.length === 0 ? (
        <p className="vacio">No hay datazos para esos filtros todavía.</p>
      ) : (
        <div className="grid">
          {datazos.map((d) => (
            <DatazoCard key={d.id} d={d} />
          ))}
        </div>
      )}
    </>
  );
}
