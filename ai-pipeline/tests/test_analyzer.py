from src.analyzer import parse_analysis_response
from src.models import VideoRecord


def _make_video(id='v1', plataforma='tiktok'):
    return VideoRecord(
        id=id, url='https://tiktok.com/v/1', plataforma=plataforma,
        cuenta='@test', descripcion='datazo mantequilla',
        fecha='2026-06-24', miniatura_url='', video_url='',
    )


def test_parse_respuesta_no_es_dazo():
    json_str = '{"es_dazo": false, "razon": "No es de la RM"}'
    result = parse_analysis_response(json_str, _make_video())
    assert result == []


def test_parse_respuesta_un_producto():
    json_str = '''[{
        "es_dazo": true,
        "producto": "Mantequilla Quillayes",
        "precio_dazo": 1000,
        "precio_supermercado": 3990,
        "ahorro_porcentaje": 75,
        "local": "Distribuidora Quillayes",
        "ubicacion_mencionada": "Maipú"
    }]'''
    result = parse_analysis_response(json_str, _make_video())
    assert len(result) == 1
    assert result[0].producto == 'Mantequilla Quillayes'
    assert result[0].precio_dazo == 1000
    assert result[0].plataforma == 'tiktok'
    assert result[0].video_crudo_id == 'v1'


def test_parse_respuesta_multiples_productos():
    json_str = '''[
        {"es_dazo": true, "producto": "Leche", "precio_dazo": 500,
         "precio_supermercado": 900, "ahorro_porcentaje": 44,
         "local": "Distrib X", "ubicacion_mencionada": "Santiago"},
        {"es_dazo": true, "producto": "Yogur", "precio_dazo": 300,
         "precio_supermercado": 700, "ahorro_porcentaje": 57,
         "local": "Distrib X", "ubicacion_mencionada": "Santiago"}
    ]'''
    result = parse_analysis_response(json_str, _make_video())
    assert len(result) == 2
    assert result[1].producto == 'Yogur'


def test_parse_respuesta_json_invalido_devuelve_vacio():
    result = parse_analysis_response('no es json', _make_video())
    assert result == []


def test_parse_respuesta_con_bloque_markdown():
    json_str = '```json\n[{"es_dazo": true, "producto": "Aceite", "precio_dazo": 2000, "precio_supermercado": null, "ahorro_porcentaje": null, "local": null, "ubicacion_mencionada": null}]\n```'
    result = parse_analysis_response(json_str, _make_video())
    assert len(result) == 1
    assert result[0].producto == 'Aceite'
