import sys
import types

from src.models import dazo_from_row, Dazo


def _row(**kw):
    base = dict(
        id='uuid-1', producto='Mantequilla', precio_dazo=1000, precio_supermercado=3990,
        ahorro_porcentaje=75, local='Distri', ubicacion_mencionada='Maipú', video_crudo_id='a',
        fuente_url='u', plataforma='tiktok', fecha_encontrado='2026-06-25', foto_producto_url=None,
        direccion='Av. X', telefono='+569', horario='L-S', maps_url='m', foto_local_url='f',
        estado='pendiente', created_at='2026-06-25T00:00:00Z',  # columnas extra
    )
    base.update(kw)
    return base


def test_dazo_from_row_ignora_columnas_extra():
    d = dazo_from_row(_row())
    assert isinstance(d, Dazo)
    assert d.producto == 'Mantequilla'
    assert d.ahorro_porcentaje == 75
    # id y created_at no son campos de Dazo y no deben romper la construcción
    assert not hasattr(d, 'created_at')


def test_publicar_dazo_registra_y_marca(monkeypatch):
    # Stubear módulos pesados ANTES de importar publicar
    llamadas = {'pub': [], 'marcado': [], 'subido': 0}

    import src.publicar as P
    monkeypatch.setattr(P, 'generar_imagen', lambda *a, **k: '/tmp/x.png')

    def fake_upload(data, name):
        llamadas['subido'] += 1
        return 'https://cdn/x.png'
    monkeypatch.setattr(P, 'upload_frame', fake_upload)

    def fake_publicar_todos(dazo, imagen_path=None, imagen_url=None, video_url=None):
        return [
            {'canal': 'telegram', 'ok': True},
            {'canal': 'whatsapp', 'ok': False, 'motivo': 'sin credenciales'},
        ]
    monkeypatch.setattr(P, 'publicar_todos', fake_publicar_todos)
    monkeypatch.setattr(P, 'save_publicacion', lambda *a, **k: llamadas['pub'].append(a))
    monkeypatch.setattr(P, 'mark_dazo_publicado', lambda did: llamadas['marcado'].append(did))
    # evitar abrir archivo real
    monkeypatch.setattr('builtins.open', lambda *a, **k: (_ for _ in ()).throw(IOError('no file')))

    exitos = P.publicar_dazo(_row())
    assert exitos == 1                       # solo telegram ok
    assert len(llamadas['pub']) == 2         # se registran ambos canales
    assert llamadas['marcado'] == ['uuid-1'] # dazo marcado publicado
