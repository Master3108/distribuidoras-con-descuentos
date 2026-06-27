from src.models import VideoRecord, Dazo, calcular_ahorro, enriquecer_precio_supermercado


def _dazo(precio_dazo=1000, precio_super=None, ahorro=None):
    return Dazo(
        producto="Mantequilla Soprole 250g",
        precio_dazo=precio_dazo,
        precio_supermercado=precio_super,
        ahorro_porcentaje=ahorro,
        local="Distribuidora X",
        ubicacion_mencionada="Maipú",
        video_crudo_id="abc",
        fuente_url="https://x",
        plataforma="tiktok",
        fecha_encontrado="2026-06-25",
        foto_producto_url=None,
    )


def test_enriquecer_usa_precio_real_y_recalcula_ahorro():
    d = _dazo(precio_dazo=1000, precio_super=3000, ahorro=67)  # estimación IA
    enriquecer_precio_supermercado(d, lambda _p: {'precio_referencia': 4000})
    assert d.precio_supermercado == 4000           # reemplaza la estimación
    assert d.ahorro_porcentaje == 75               # (1 - 1000/4000)

def test_enriquecer_conserva_estimacion_si_no_hay_precio_real():
    d = _dazo(precio_dazo=1000, precio_super=3990, ahorro=75)
    enriquecer_precio_supermercado(d, lambda _p: None)
    assert d.precio_supermercado == 3990           # se mantiene lo de la IA
    assert d.ahorro_porcentaje == 75

def test_calcular_ahorro_con_ambos_precios():
    assert calcular_ahorro(1000, 3990) == 75

def test_calcular_ahorro_sin_precio_supermercado():
    assert calcular_ahorro(1000, None) is None

def test_calcular_ahorro_precio_supermercado_cero():
    assert calcular_ahorro(1000, 0) is None

def test_video_record_campos_minimos():
    v = VideoRecord(
        id="abc123",
        url="https://tiktok.com/...",
        plataforma="tiktok",
        cuenta="@test",
        descripcion="datazo",
        fecha="2026-06-24",
        miniatura_url="https://example.com/thumb.jpg",
        video_url="",
    )
    assert v.id == "abc123"
    assert v.plataforma == "tiktok"

def test_dazo_campos_requeridos():
    d = Dazo(
        producto="Mantequilla Quillayes",
        precio_dazo=1000,
        precio_supermercado=3990,
        ahorro_porcentaje=75,
        local="Distribuidora Quillayes",
        ubicacion_mencionada="Maipú",
        video_crudo_id="abc123",
        fuente_url="https://tiktok.com/...",
        plataforma="tiktok",
        fecha_encontrado="2026-06-24",
        foto_producto_url=None,
    )
    assert d.producto == "Mantequilla Quillayes"
    assert d.precio_dazo == 1000
