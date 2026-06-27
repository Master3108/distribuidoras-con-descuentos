import src.enriquecimiento as enr
from src.models import Dazo, enriquecer_local


def _place():
    return {
        'displayName': {'text': 'Distribuidora Quillayes'},
        'formattedAddress': 'Av. 5 de Abril 1234, Maipú, Chile',
        'nationalPhoneNumber': '+56 9 1234 5678',
        'regularOpeningHours': {'weekdayDescriptions': ['lunes: 8–18', 'martes: 8–18']},
        'googleMapsUri': 'https://maps.google.com/?cid=123',
        'photos': [{'name': 'places/ABC/photos/XYZ'}],
    }


def test_normalizar_lugar_mapea_campos(monkeypatch):
    monkeypatch.setattr(enr, 'PLACES_KEY', 'k')
    out = enr.normalizar_lugar(_place())
    assert out['direccion'].startswith('Av. 5 de Abril')
    assert out['telefono'] == '+56 9 1234 5678'
    assert out['horario'] == 'lunes: 8–18; martes: 8–18'
    assert out['maps_url'].startswith('https://maps.google.com')
    assert 'places/ABC/photos/XYZ/media' in out['foto_local_url']


def test_normalizar_lugar_sin_fotos(monkeypatch):
    monkeypatch.setattr(enr, 'PLACES_KEY', 'k')
    p = _place()
    p.pop('photos')
    assert enr.normalizar_lugar(p)['foto_local_url'] is None


def test_normalizar_osm_mapea_direccion_y_maps():
    item = {'display_name': 'Jumbo, Avenida Pajaritos, Maipú, Chile', 'lat': '-33.51', 'lon': '-70.76'}
    out = enr.normalizar_osm(item)
    assert out['direccion'].startswith('Jumbo')
    assert out['maps_url'] == 'https://www.google.com/maps/search/?api=1&query=-33.51,-70.76'
    assert out['telefono'] is None and out['horario'] is None


def _dazo(local='Distribuidora Quillayes', comuna='Maipú'):
    return Dazo(
        producto='Mantequilla', precio_dazo=1000, precio_supermercado=3990, ahorro_porcentaje=75,
        local=local, ubicacion_mencionada=comuna, video_crudo_id='a', fuente_url='u',
        plataforma='tiktok', fecha_encontrado='2026-06-25', foto_producto_url=None,
    )


def test_enriquecer_local_rellena_y_queda_pendiente():
    d = _dazo()
    enriquecer_local(d, lambda n, c: {
        'direccion': 'Av. 5 de Abril 1234, Maipú', 'telefono': '+569...',
        'horario': 'Lun-Sáb', 'maps_url': 'https://maps...', 'foto_local_url': 'https://img',
    })
    assert d.direccion.startswith('Av. 5 de Abril')
    assert d.estado == 'pendiente'  # tiene dirección → completo


def test_enriquecer_local_sin_resultado_queda_incompleto():
    d = _dazo()
    enriquecer_local(d, lambda n, c: None)
    assert d.estado == 'incompleto'
    assert d.direccion is None


def test_enriquecer_local_sin_nombre_de_local_incompleto():
    d = _dazo(local=None)
    enriquecer_local(d, lambda n, c: {'direccion': 'x'})  # no debería ni llamarse
    assert d.estado == 'incompleto'
