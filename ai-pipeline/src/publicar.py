"""Publicador espaciado. Lo ejecuta el cron varias veces al día: toma los
datazos pendientes (mayor ahorro primero), genera la imagen, la sube, publica en
todos los canales disponibles, registra el resultado y marca el dazo publicado.

    08:00 → publica el de mayor ahorro
    11:00 → siguiente
    ...

Separado de main.py (que solo extrae): así se controla el ritmo de publicación.
"""
import os
try:
    import dotenv
    dotenv.load_dotenv()
except ModuleNotFoundError:
    pass

from src.models import dazo_from_row
from src.storage import fetch_datazos_pendientes, mark_dazo_publicado, save_publicacion, upload_frame
from src.generador import generar_imagen
from src.publicador import publicar_todos

PUBLICAR_BATCH = int(os.environ.get('PUBLICAR_BATCH', '1'))


def publicar_dazo(row: dict) -> int:
    """Publica un datazo (fila de BD). Devuelve cuántos canales tuvieron éxito."""
    dazo = dazo_from_row(row)
    dazo_id = row['id']

    # Generar imagen de marca y subirla para tener URL pública (IG/WhatsApp/FB
    # necesitan URL; Telegram usa el archivo local).
    imagen_path = generar_imagen(dazo, foto_path=None, formato='post')
    imagen_url = None
    try:
        with open(imagen_path, 'rb') as f:
            imagen_url = upload_frame(f.read(), f'post_{dazo_id}.png')
    except Exception as e:
        print(f'  No se pudo subir la imagen: {e}')

    resultados = publicar_todos(dazo, imagen_path=imagen_path, imagen_url=imagen_url)

    exitos = 0
    for r in resultados:
        save_publicacion(dazo_id, r['canal'], r['ok'], r.get('error') or r.get('motivo'))
        if r['ok']:
            exitos += 1
        print(f"    {r['canal']}: {'✅' if r['ok'] else '—'} {r.get('motivo') or r.get('error') or ''}".rstrip())

    mark_dazo_publicado(dazo_id)
    return exitos


def main():
    pendientes = fetch_datazos_pendientes(limit=PUBLICAR_BATCH)
    print(f'publicador: {len(pendientes)} datazo(s) pendiente(s)')
    for row in pendientes:
        print(f"→ {row.get('producto')} (ahorro {row.get('ahorro_porcentaje')}%)")
        publicar_dazo(row)
    print('publicador: listo')


if __name__ == '__main__':
    main()
