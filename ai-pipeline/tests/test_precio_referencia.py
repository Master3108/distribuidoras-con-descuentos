import json
import src.precio_referencia as pr


def test_norm():
    assert pr._norm('  Coca   Cola 1.5L ') == 'coca cola 1.5l'


def test_parse_stdout_json_limpio():
    assert pr._parse_stdout('{"mejor": {"precio": 1990}}')['mejor']['precio'] == 1990


def test_parse_stdout_con_ruido_alrededor():
    salida = 'ExperimentalWarning: ...\n{"mejor": {"precio": 1000}}\nlisto'
    assert pr._parse_stdout(salida)['mejor']['precio'] == 1000


def test_parse_stdout_basura():
    assert pr._parse_stdout('no es json') is None
    assert pr._parse_stdout('') is None


def test_precio_referencia_toma_mediana_de_mercados(tmp_path, monkeypatch):
    monkeypatch.setattr(pr, 'ENABLED', True)
    monkeypatch.setattr(pr, 'CACHE_PATH', tmp_path / 'cache.json')
    precios = {'jumbo': 1990, 'santaisabel': 2090, 'unimarc': 1890}
    monkeypatch.setattr(pr, 'consultar_mercado', lambda prod, m: {'precio': precios[m]})

    out = pr.precio_referencia('coca cola', mercados=['jumbo', 'santaisabel', 'unimarc'])
    assert out['precio_referencia'] == 1990  # mediana de 1890/1990/2090
    assert out['detalle'] == precios


def test_precio_referencia_none_si_ningun_mercado_responde(tmp_path, monkeypatch):
    monkeypatch.setattr(pr, 'ENABLED', True)
    monkeypatch.setattr(pr, 'CACHE_PATH', tmp_path / 'cache.json')
    monkeypatch.setattr(pr, 'consultar_mercado', lambda prod, m: None)
    assert pr.precio_referencia('producto inexistente', mercados=['jumbo']) is None


def test_precio_referencia_usa_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(pr, 'ENABLED', True)
    monkeypatch.setattr(pr, 'CACHE_PATH', tmp_path / 'cache.json')
    llamadas = {'n': 0}

    def fake(prod, m):
        llamadas['n'] += 1
        return {'precio': 1500}

    monkeypatch.setattr(pr, 'consultar_mercado', fake)
    pr.precio_referencia('leche', mercados=['jumbo'])
    pr.precio_referencia('leche', mercados=['jumbo'])  # segunda vez → caché
    assert llamadas['n'] == 1  # solo se consultó una vez


def test_precio_referencia_desactivado(monkeypatch):
    monkeypatch.setattr(pr, 'ENABLED', False)
    assert pr.precio_referencia('coca cola') is None
