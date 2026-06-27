"""Prueba end-to-end del cableado del pipeline (servicios externos mockeados).

Recorre la cadena completa para un datazo: análisis → precio real de
supermercado → enriquecimiento del local → imagen de marca → caption →
publicación. Verifica que todas las piezas encajan, sin llamar a APIs reales.
"""
from pathlib import Path

from PIL import Image

from src.models import Dazo, enriquecer_precio_supermercado, enriquecer_local
from src.generador import generar_imagen, FORMATOS
from src.publicador import construir_caption, publicar_todos


def test_flujo_completo(tmp_path, monkeypatch):
    # 1. Lo que entregaría el análisis de Gemini (sin precio de super confiable)
    dazo = Dazo(
        producto='Mantequilla Sin Lactosa Quillayes 250g', precio_dazo=1000,
        precio_supermercado=None, ahorro_porcentaje=None,
        local='Distribuidora Quillayes', ubicacion_mencionada='Maipú',
        video_crudo_id='v1', fuente_url='https://tiktok.com/x', plataforma='tiktok',
        fecha_encontrado='2026-06-25', foto_producto_url=None,
    )

    # 2. Precio REAL de supermercado (extractor mockeado) → recalcula ahorro
    enriquecer_precio_supermercado(dazo, lambda _p: {'precio_referencia': 4000})
    assert dazo.precio_supermercado == 4000
    assert dazo.ahorro_porcentaje == 75

    # 3. Enriquecimiento del local (Places mockeado)
    enriquecer_local(dazo, lambda n, c: {
        'direccion': 'Av. 5 de Abril 1234, Maipú', 'telefono': '+56 9 1234 5678',
        'horario': 'Lun-Sáb 8-18', 'maps_url': 'https://maps...', 'foto_local_url': 'https://img',
    })
    assert dazo.direccion and dazo.estado == 'pendiente'

    # 4. Imagen de marca
    img = generar_imagen(dazo, formato='post', out_dir=str(tmp_path))
    assert Path(img).exists()
    with Image.open(img) as im:
        assert im.size == FORMATOS['post']

    # 5. Caption con todos los datos enriquecidos
    cap = construir_caption(dazo)
    assert 'Mantequilla' in cap
    assert 'ahorras 75%' in cap
    assert 'Av. 5 de Abril 1234' in cap

    # 6. Publicación sin credenciales → todo se omite, sin excepciones
    for v in ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'WHATSAPP_TOKEN', 'WHATSAPP_PHONE_ID',
              'WHATSAPP_TO', 'META_TOKEN', 'FB_PAGE_ID', 'IG_USER_ID', 'TIKTOK_TOKEN']:
        monkeypatch.delenv(v, raising=False)
    resultados = publicar_todos(dazo, imagen_path=img, imagen_url='https://cdn/x.png')
    assert len(resultados) == 5
    assert all(r['ok'] is False for r in resultados)  # sin creds no publica, pero no rompe
