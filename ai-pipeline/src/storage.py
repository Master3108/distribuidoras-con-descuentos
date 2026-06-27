"""Acceso a datos vía Supabase REST (supabase-py) sobre HTTPS.

Usa SUPABASE_SERVICE_KEY (service_role) para escribir saltándose RLS. La web lee
con la anon key. Se eligió REST en vez de Postgres directo porque la conexión
directa de Supabase es IPv6-only; el REST funciona desde cualquier lado.
"""
import os

from src.models import VideoRecord, Dazo

_client = None


def _get_client():
    """Cliente Supabase bajo demanda (import lazy: los tests no requieren supabase)."""
    global _client
    if _client is None:
        from supabase import create_client
        _client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])
    return _client


def fetch_unprocessed_videos(limit: int = 10) -> list[VideoRecord]:
    res = _get_client().table('videos_crudos').select('*') \
        .eq('procesado', False).order('fecha_encontrado', desc=False).limit(limit).execute()
    cols = {'id', 'url', 'plataforma', 'cuenta', 'descripcion', 'fecha', 'miniatura_url', 'video_url'}
    return [VideoRecord(**{k: v for k, v in row.items() if k in cols}) for row in res.data]


def mark_video_processed(video_id: str) -> None:
    _get_client().table('videos_crudos').update({'procesado': True}).eq('id', video_id).execute()


def save_dazo(dazo: Dazo) -> str:
    """Inserta un datazo y devuelve su id."""
    row = {
        'producto': dazo.producto, 'precio_dazo': dazo.precio_dazo,
        'precio_supermercado': dazo.precio_supermercado, 'ahorro_porcentaje': dazo.ahorro_porcentaje,
        'local': dazo.local, 'ubicacion_mencionada': dazo.ubicacion_mencionada,
        'foto_producto_url': dazo.foto_producto_url, 'direccion': dazo.direccion,
        'telefono': dazo.telefono, 'horario': dazo.horario, 'maps_url': dazo.maps_url,
        'foto_local_url': dazo.foto_local_url, 'video_crudo_id': dazo.video_crudo_id,
        'fuente_url': dazo.fuente_url, 'plataforma': dazo.plataforma,
        'fecha_encontrado': dazo.fecha_encontrado, 'estado': dazo.estado,
    }
    res = _get_client().table('datazos').insert(row).execute()
    return res.data[0]['id'] if res.data else ''


def fetch_datazos_pendientes(limit: int = 1) -> list[dict]:
    res = _get_client().table('datazos').select('*') \
        .eq('estado', 'pendiente').order('ahorro_porcentaje', desc=True).limit(limit).execute()
    return res.data or []


def mark_dazo_publicado(dazo_id: str) -> None:
    _get_client().table('datazos').update({'estado': 'publicado'}).eq('id', dazo_id).execute()


def save_publicacion(dazo_id: str, canal: str, ok: bool, detalle: str = None) -> None:
    _get_client().table('publicaciones').insert(
        {'dazo_id': dazo_id, 'canal': canal, 'ok': ok, 'detalle': detalle}).execute()


def upload_frame(image_bytes: bytes, filename: str):
    """Sube la imagen al bucket público 'datazos-frames' y devuelve su URL pública.
    Devuelve None si falla (Telegram igual publica con el archivo local)."""
    try:
        client = _get_client()
        bucket = 'datazos-frames'
        client.storage.from_(bucket).upload(
            path=filename, file=image_bytes,
            file_options={'content-type': 'image/jpeg', 'upsert': 'true'})
        return client.storage.from_(bucket).get_public_url(filename)
    except Exception as e:
        print(f'  upload_frame falló: {e}')
        return None
