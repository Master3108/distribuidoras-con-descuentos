import subprocess
import tempfile
import os


def frames_from_image(image_path: str) -> list[str]:
    """Wrapper para imágenes estáticas — devuelve [image_path] directamente."""
    return [image_path]


def frames_from_video(video_path: str, num_frames: int = 5) -> list[str]:
    """Extrae num_frames fotogramas equidistantes del video con FFmpeg.
    Devuelve lista de rutas temporales o [] si FFmpeg falla."""
    if not os.path.exists(video_path):
        return []

    tmp_dir = tempfile.mkdtemp()
    output_pattern = os.path.join(tmp_dir, 'frame_%03d.jpg')

    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', f'fps=1/5,select=not(mod(n\\,{max(1, num_frames)}))',
        '-frames:v', str(num_frames),
        '-q:v', '2',
        output_pattern,
        '-y', '-loglevel', 'error',
    ]

    try:
        subprocess.run(cmd, check=True, timeout=60)
        frames = sorted([
            os.path.join(tmp_dir, f)
            for f in os.listdir(tmp_dir)
            if f.endswith('.jpg')
        ])
        return frames[:num_frames]
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return []
