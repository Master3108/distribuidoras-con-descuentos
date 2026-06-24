import os
from supabase import create_client, Client
from src.models import VideoRecord, Dazo

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(
            os.environ['SUPABASE_URL'],
            os.environ['SUPABASE_SERVICE_KEY'],
        )
    return _client


def fetch_unprocessed_videos(limit: int = 10) -> list[VideoRecord]:
    res = _get_client().table('videos_crudos') \
        .select('*') \
        .eq('procesado', False) \
        .order('fecha_encontrado', desc=False) \
        .limit(limit) \
        .execute()
    return [VideoRecord(**row) for row in res.data]


def mark_video_processed(video_id: str) -> None:
    _get_client().table('videos_crudos') \
        .update({'procesado': True}) \
        .eq('id', video_id) \
        .execute()


def save_dazo(dazo: Dazo) -> None:
    row = {
        'producto': dazo.producto,
        'precio_dazo': dazo.precio_dazo,
        'precio_supermercado': dazo.precio_supermercado,
        'ahorro_porcentaje': dazo.ahorro_porcentaje,
        'local': dazo.local,
        'ubicacion_mencionada': dazo.ubicacion_mencionada,
        'foto_producto_url': dazo.foto_producto_url,
        'video_crudo_id': dazo.video_crudo_id,
        'fuente_url': dazo.fuente_url,
        'plataforma': dazo.plataforma,
        'fecha_encontrado': dazo.fecha_encontrado,
        'estado': 'pendiente',
    }
    _get_client().table('datazos').insert(row).execute()


def upload_frame(image_bytes: bytes, filename: str) -> str:
    """Sube imagen a Supabase Storage bucket 'datazos-frames' y devuelve URL pública."""
    bucket = 'datazos-frames'
    client = _get_client()
    client.storage.from_(bucket).upload(
        path=filename,
        file=image_bytes,
        file_options={'content-type': 'image/jpeg', 'upsert': 'true'},
    )
    res = client.storage.from_(bucket).get_public_url(filename)
    return res
