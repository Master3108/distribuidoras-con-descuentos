export default function Filtros({ q, comuna }: { q: string; comuna: string }) {
  // Form GET → los filtros viajan por la URL (?q=&comuna=), server-side.
  return (
    <form className="filtros" method="get">
      <input type="text" name="q" placeholder="Buscar producto…" defaultValue={q} />
      <input type="text" name="comuna" placeholder="Comuna (ej. Maipú)" defaultValue={comuna} />
      <button type="submit">Filtrar</button>
    </form>
  );
}
