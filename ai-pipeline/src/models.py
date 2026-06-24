from dataclasses import dataclass
from typing import Optional


@dataclass
class VideoRecord:
    id: str
    url: str
    plataforma: str
    cuenta: str
    descripcion: str
    fecha: str
    miniatura_url: str
    video_url: str


@dataclass
class Dazo:
    producto: str
    precio_dazo: int
    precio_supermercado: Optional[int]
    ahorro_porcentaje: Optional[int]
    local: Optional[str]
    ubicacion_mencionada: Optional[str]
    video_crudo_id: str
    fuente_url: str
    plataforma: str
    fecha_encontrado: str
    foto_producto_url: Optional[str]


def calcular_ahorro(precio_dazo: int, precio_supermercado: Optional[int]) -> Optional[int]:
    if not precio_supermercado:
        return None
    return round((1 - precio_dazo / precio_supermercado) * 100)
