from PIL import Image

from src.generador import generar_imagen, _clp, _envolver, FORMATOS
from src.models import Dazo
from PIL import ImageDraw, ImageFont


def _dazo():
    return Dazo(
        producto='Mantequilla Sin Lactosa Quillayes 250g',
        precio_dazo=1000, precio_supermercado=3990, ahorro_porcentaje=75,
        local='Distribuidora Quillayes', ubicacion_mencionada='Maipú',
        video_crudo_id='a', fuente_url='u', plataforma='tiktok',
        fecha_encontrado='2026-06-25', foto_producto_url=None,
        direccion='Av. 5 de Abril 1234, Maipú', telefono='+56 9 1234 5678',
        horario='Lun-Sáb 8-18',
    )


def test_clp_formato_chileno():
    assert _clp(1000) == '$1.000'
    assert _clp(3990) == '$3.990'
    assert _clp(1234567) == '$1.234.567'
    assert _clp(None) == ''


def test_envolver_respeta_ancho_y_max_3_lineas():
    img = Image.new('RGB', (100, 100))
    d = ImageDraw.Draw(img)
    f = ImageFont.load_default()
    lineas = _envolver(d, 'una dos tres cuatro cinco seis siete ocho', f, 40)
    assert len(lineas) <= 3


def test_generar_imagen_post_crea_png_correcto(tmp_path):
    ruta = generar_imagen(_dazo(), formato='post', out_dir=str(tmp_path))
    assert ruta.endswith('.png')
    with Image.open(ruta) as im:
        assert im.size == FORMATOS['post']
        assert im.format == 'PNG'


def test_generar_imagen_story_dimensiones(tmp_path):
    ruta = generar_imagen(_dazo(), formato='story', out_dir=str(tmp_path))
    with Image.open(ruta) as im:
        assert im.size == FORMATOS['story']


def test_generar_imagen_sin_foto_no_falla(tmp_path):
    d = _dazo()
    d.precio_supermercado = None
    d.ahorro_porcentaje = None
    ruta = generar_imagen(d, foto_path='/no/existe.jpg', formato='post', out_dir=str(tmp_path))
    assert Image.open(ruta).size == FORMATOS['post']
