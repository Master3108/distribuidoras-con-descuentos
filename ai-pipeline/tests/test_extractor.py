import os
import tempfile
from PIL import Image
from src.extractor import frames_from_image, frames_from_video


def test_frames_from_image_devuelve_lista_con_la_imagen():
    img = Image.new('RGB', (100, 100), color=(255, 0, 0))
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        img.save(f.name)
        path = f.name
    try:
        result = frames_from_image(path)
        assert len(result) == 1
        assert result[0] == path
    finally:
        os.unlink(path)


def test_frames_from_video_devuelve_lista_vacia_si_ffmpeg_falla():
    result = frames_from_video('/archivo/no/existe.mp4', num_frames=3)
    assert result == []
