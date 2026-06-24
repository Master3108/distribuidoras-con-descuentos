from src.models import VideoRecord, Dazo, calcular_ahorro

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
