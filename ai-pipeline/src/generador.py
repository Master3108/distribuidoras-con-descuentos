"""Generador de contenido: arma la imagen de marca de cada datazo (Pillow) y,
opcionalmente, un video corto animado (FFmpeg).

Un producto = un post. La identidad visual (colores, layout) se define una sola
vez aquí como constantes.
"""
import os
import subprocess
import tempfile
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from src.models import Dazo

# ─── Identidad visual ────────────────────────────────────────────────────────
COLOR_BG = (17, 24, 39)        # navy oscuro
COLOR_HEADER = (216, 90, 48)   # coral
COLOR_ACCENT = (248, 230, 136) # amarillo
COLOR_TEXT = (255, 255, 255)
COLOR_MUTED = (170, 178, 190)
COLOR_TACHADO = (150, 120, 120)

FORMATOS = {
    'post': (1080, 1080),
    'story': (1080, 1920),
}

_FUENTES_BOLD = [os.environ.get('BRAND_FONT_BOLD'), 'C:/Windows/Fonts/arialbd.ttf',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']
_FUENTES_REG = [os.environ.get('BRAND_FONT'), 'C:/Windows/Fonts/arial.ttf',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for ruta in (_FUENTES_BOLD if bold else _FUENTES_REG):
        if ruta and os.path.exists(ruta):
            try:
                return ImageFont.truetype(ruta, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _clp(n: Optional[int]) -> str:
    return '' if n is None else '$' + f'{int(n):,}'.replace(',', '.')


def _centrar(draw, cx, y, texto, font, fill):
    w = draw.textlength(texto, font=font)
    draw.text((cx - w / 2, y), texto, font=font, fill=fill)
    return w


def _envolver(draw, texto, font, max_w):
    palabras, lineas, actual = texto.split(), [], ''
    for p in palabras:
        prueba = f'{actual} {p}'.strip()
        if draw.textlength(prueba, font=font) <= max_w:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    return lineas[:3]


def generar_imagen(dazo: Dazo, foto_path: Optional[str] = None,
                   formato: str = 'post', out_dir: Optional[str] = None) -> str:
    """Genera la imagen de marca del datazo y devuelve la ruta del PNG."""
    W, H = FORMATOS.get(formato, FORMATOS['post'])
    img = Image.new('RGB', (W, H), COLOR_BG)
    d = ImageDraw.Draw(img)
    cx = W // 2
    pad = 70

    # Banda de encabezado
    d.rectangle([0, 0, W, 150], fill=COLOR_HEADER)
    _centrar(d, cx, 48, 'DATAZO DEL DÍA', _font(58, bold=True), COLOR_TEXT)

    # Foto del producto (cover) o marco placeholder
    foto_top, foto_h = 190, int(H * 0.34)
    caja = [pad, foto_top, W - pad, foto_top + foto_h]
    if foto_path and os.path.exists(foto_path):
        try:
            prod = Image.open(foto_path).convert('RGB')
            bw, bh = caja[2] - caja[0], caja[3] - caja[1]
            escala = max(bw / prod.width, bh / prod.height)
            prod = prod.resize((int(prod.width * escala), int(prod.height * escala)))
            ox = caja[0] + (bw - prod.width) // 2
            oy = caja[1] + (bh - prod.height) // 2
            img.paste(prod, (ox, oy))
        except Exception:
            d.rectangle(caja, outline=COLOR_MUTED, width=3)
    else:
        d.rectangle(caja, outline=COLOR_MUTED, width=3)
        _centrar(d, cx, caja[1] + foto_h // 2 - 20, 'sin foto', _font(40), COLOR_MUTED)

    y = caja[3] + 40

    # Nombre del producto (hasta 3 líneas)
    fp = _font(56, bold=True)
    for linea in _envolver(d, dazo.producto, fp, W - 2 * pad):
        _centrar(d, cx, y, linea, fp, COLOR_TEXT)
        y += 66
    y += 20

    # Precio dazo + precio supermercado tachado
    precio = _clp(dazo.precio_dazo)
    _centrar(d, cx, y, precio, _font(120, bold=True), COLOR_ACCENT)
    y += 140
    if dazo.precio_supermercado:
        ref = _clp(dazo.precio_supermercado)
        fref = _font(48)
        w = _centrar(d, cx, y, ref, fref, COLOR_TACHADO)
        d.line([cx - w / 2, y + 28, cx + w / 2, y + 28], fill=COLOR_TACHADO, width=4)
        y += 64

    # Ahorro
    if dazo.ahorro_porcentaje:
        _centrar(d, cx, y, f'AHORRAS UN {dazo.ahorro_porcentaje}%', _font(56, bold=True), COLOR_HEADER)
        y += 80

    # Datos del local
    floc = _font(38)
    for txt in filter(None, [dazo.local, dazo.direccion, dazo.telefono, dazo.horario]):
        _centrar(d, cx, y, txt[:48], floc, COLOR_MUTED)
        y += 50

    out_dir = out_dir or tempfile.mkdtemp()
    out_path = os.path.join(out_dir, f'dazo_{formato}.png')
    img.save(out_path, 'PNG')
    return out_path


def generar_video(imagen_path: str, out_dir: Optional[str] = None, dur: int = 6) -> Optional[str]:
    """Crea un video corto con un zoom suave sobre la imagen (FFmpeg).
    Devuelve la ruta del mp4 o None si FFmpeg no está disponible."""
    if not imagen_path or not os.path.exists(imagen_path):
        return None
    out_dir = out_dir or tempfile.mkdtemp()
    out_path = os.path.join(out_dir, 'dazo.mp4')
    cmd = [
        'ffmpeg', '-loop', '1', '-i', imagen_path, '-t', str(dur),
        '-vf', f"zoompan=z='min(zoom+0.0006,1.10)':d={dur*25}:s=1080x1080,format=yuv420p",
        '-r', '25', out_path, '-y', '-loglevel', 'error',
    ]
    try:
        subprocess.run(cmd, check=True, timeout=120)
        return out_path
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None
