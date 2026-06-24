import os
import dotenv
dotenv.load_dotenv()

from src.models import VideoRecord
from src.storage import fetch_unprocessed_videos, mark_video_processed, save_dazo, upload_frame
from src.downloader import download_thumbnail, download_video, cleanup
from src.extractor import frames_from_image, frames_from_video
from src.transcriber import transcribe_audio
from src.analyzer import analyze_video

BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '10'))


def process_video(video: VideoRecord) -> int:
    """Procesa un video. Devuelve número de datazos encontrados."""
    tmp_thumbnail = None
    tmp_video = None
    extra_frames = []
    datazos_count = 0

    try:
        # 1. Descargar thumbnail (siempre disponible)
        tmp_thumbnail = download_thumbnail(video.miniatura_url)
        frames = frames_from_image(tmp_thumbnail) if tmp_thumbnail else []

        # 2. Intentar descargar video para frames adicionales + audio
        transcript = ''
        tmp_video = download_video(video.video_url)
        if tmp_video:
            extra_frames = frames_from_video(tmp_video, num_frames=4)
            if extra_frames:
                frames = extra_frames
            transcript = transcribe_audio(tmp_video)

        if not frames:
            print(f'  Sin frames para {video.id} — saltando')
            return 0

        # 3. Analizar con Claude Vision
        datazos = analyze_video(frames, transcript, video)

        # 4. Subir foto del producto y guardar cada dazo
        for dazo in datazos:
            foto_url = None
            if frames:
                with open(frames[0], 'rb') as f:
                    foto_url = upload_frame(f.read(), f'dazo_{video.id}_{dazo.producto[:20]}.jpg')
            dazo.foto_producto_url = foto_url
            save_dazo(dazo)
            datazos_count += 1
            print(f'  ✅ Dazo: {dazo.producto} ${dazo.precio_dazo:,} — {dazo.local}')

    except Exception as e:
        print(f'  Error procesando {video.id}: {e}')

    finally:
        cleanup(tmp_thumbnail)
        cleanup(tmp_video)
        for f in extra_frames:
            cleanup(f)

    return datazos_count


def main():
    print(f'ai-pipeline iniciando — batch size: {BATCH_SIZE}')
    videos = fetch_unprocessed_videos(limit=BATCH_SIZE)
    print(f'{len(videos)} videos sin procesar encontrados')

    total_datazos = 0
    for i, video in enumerate(videos, 1):
        print(f'[{i}/{len(videos)}] {video.plataforma} {video.cuenta} — {video.id}')
        count = process_video(video)
        mark_video_processed(video.id)
        total_datazos += count

    print(f'\n✅ ai-pipeline completado. {total_datazos} datazos extraídos de {len(videos)} videos.')


if __name__ == '__main__':
    main()
