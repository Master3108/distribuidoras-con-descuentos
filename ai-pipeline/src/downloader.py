import httpx
import tempfile
import os


def download_to_temp(url: str, suffix: str = '.jpg') -> str | None:
    """Descarga URL a archivo temporal. Devuelve ruta o None si falla."""
    if not url:
        return None
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(response.content)
        tmp.close()
        return tmp.name
    except Exception as e:
        print(f'Download failed for {url}: {e}')
        return None


def download_thumbnail(url: str) -> str | None:
    return download_to_temp(url, suffix='.jpg')


def download_video(url: str) -> str | None:
    return download_to_temp(url, suffix='.mp4')


def cleanup(path: str | None) -> None:
    if path and os.path.exists(path):
        os.unlink(path)
