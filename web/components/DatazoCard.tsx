import { Datazo, clp } from '../lib/supabase';

export default function DatazoCard({ d }: { d: Datazo }) {
  return (
    <article className="card">
      {d.foto_producto_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img className="foto" src={d.foto_producto_url} alt={d.producto} />
      ) : (
        <div className="foto" />
      )}
      <div className="body">
        <div className="nombre">{d.producto}</div>
        <div>
          <span className="precio">{clp(d.precio_dazo)}</span>
          {d.precio_supermercado ? <span className="ref">{clp(d.precio_supermercado)}</span> : null}
        </div>
        {d.ahorro_porcentaje ? <span className="ahorro">AHORRAS {d.ahorro_porcentaje}%</span> : null}
        {d.local ? (
          <div className="local">
            📍 {d.local}
            {d.ubicacion_mencionada ? `, ${d.ubicacion_mencionada}` : ''}
          </div>
        ) : null}
        {d.direccion ? <div className="local">{d.direccion}</div> : null}
        {d.telefono ? <div className="local">📞 {d.telefono}</div> : null}
        {d.horario ? <div className="local">🕐 {d.horario}</div> : null}
        {d.maps_url ? (
          <div className="local">
            <a href={d.maps_url} target="_blank" rel="noreferrer">Ver en Maps</a>
          </div>
        ) : null}
      </div>
    </article>
  );
}
