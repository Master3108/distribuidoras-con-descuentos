import src.publicador as pub
from src.models import Dazo


def _dazo(**kw):
    base = dict(
        producto='Mantequilla Quillayes', precio_dazo=1000, precio_supermercado=3990,
        ahorro_porcentaje=75, local='Distribuidora Quillayes', ubicacion_mencionada='Maipú',
        video_crudo_id='a', fuente_url='u', plataforma='tiktok', fecha_encontrado='2026-06-25',
        foto_producto_url=None, direccion='Av. 5 de Abril 1234', telefono='+56 9 1234 5678',
        horario='Lun-Sáb 8-18',
    )
    base.update(kw)
    return Dazo(**base)


def test_caption_incluye_datos_clave():
    c = pub.construir_caption(_dazo())
    assert 'Mantequilla Quillayes' in c
    assert '$1.000' in c
    assert 'ahorras 75%' in c
    assert 'Maipú' in c
    assert '+56 9 1234 5678' in c


def test_caption_sin_ahorro_omite_linea():
    c = pub.construir_caption(_dazo(precio_supermercado=None, ahorro_porcentaje=None))
    assert 'ahorras' not in c
    assert '$1.000' in c


def test_canales_se_omiten_sin_credenciales(monkeypatch):
    for v in ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'WHATSAPP_TOKEN', 'WHATSAPP_PHONE_ID',
              'WHATSAPP_TO', 'META_TOKEN', 'FB_PAGE_ID', 'IG_USER_ID', 'TIKTOK_TOKEN']:
        monkeypatch.delenv(v, raising=False)
    resultados = pub.publicar_todos(_dazo(), imagen_path=None, imagen_url='https://x/i.png')
    canales = {r['canal'] for r in resultados}
    assert canales == {'telegram', 'whatsapp', 'facebook', 'instagram', 'tiktok'}
    assert all(r['ok'] is False for r in resultados)  # sin credenciales → nada se publica


def test_telegram_envia_con_credenciales(monkeypatch):
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'tok')
    monkeypatch.setenv('TELEGRAM_CHAT_ID', '123')

    class FakeResp:
        def json(self):
            return {'ok': True}

    llamado = {}

    def fake_post(url, **kw):
        llamado['url'] = url
        return FakeResp()

    monkeypatch.setattr(pub.httpx, 'post', fake_post)
    r = pub.publicar_telegram(_dazo(), 'hola', imagen_path=None)
    assert r == {'canal': 'telegram', 'ok': True}
    assert 'sendMessage' in llamado['url']  # sin imagen → mensaje de texto


def test_tiktok_reporta_que_requiere_aprobacion(monkeypatch):
    monkeypatch.delenv('TIKTOK_TOKEN', raising=False)
    r = pub.publicar_tiktok(_dazo(), 'cap', None)
    assert r['ok'] is False and 'aprobación' in r['motivo']
