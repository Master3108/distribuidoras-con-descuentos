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
    # Enriquecimiento del local (Google Places) — se llenan en el paso 3
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    horario: Optional[str] = None
    maps_url: Optional[str] = None
    foto_local_url: Optional[str] = None
    # pendiente | publicado | incompleto
    estado: str = 'pendiente'


_DAZO_FIELDS = set(Dazo.__dataclass_fields__.keys())


def dazo_from_row(row: dict) -> Dazo:
    """Reconstruye un Dazo desde una fila de la tabla `datazos` (ignora columnas
    extra como id, created_at)."""
    return Dazo(**{k: v for k, v in row.items() if k in _DAZO_FIELDS})


def calcular_ahorro(precio_dazo: int, precio_supermercado: Optional[int]) -> Optional[int]:
    if not precio_supermercado:
        return None
    return round((1 - precio_dazo / precio_supermercado) * 100)


def enriquecer_precio_supermercado(dazo: 'Dazo', lookup) -> 'Dazo':
    """Reemplaza el precio_supermercado adivinado por la IA con el precio REAL
    consultado en los supermercados, y recalcula el ahorro.

    `lookup(producto)` devuelve {'precio_referencia': int, ...} o None. Si no hay
    precio real, se conserva lo que ya tenía el dazo (la estimación de la IA).
    """
    ref = lookup(dazo.producto)
    if ref and ref.get('precio_referencia'):
        dazo.precio_supermercado = ref['precio_referencia']
        dazo.ahorro_porcentaje = calcular_ahorro(dazo.precio_dazo, dazo.precio_supermercado)
    return dazo


def enriquecer_local(dazo: 'Dazo', lookup) -> 'Dazo':
    """Rellena dirección, teléfono, horario, maps y foto del local usando
    `lookup(nombre, comuna)` (Google Places). Si no hay dirección, marca el dazo
    como 'incompleto' (no se publicará automáticamente, según el diseño).
    """
    if dazo.local:
        info = lookup(dazo.local, dazo.ubicacion_mencionada)
        if info:
            dazo.direccion = info.get('direccion') or dazo.direccion
            dazo.telefono = info.get('telefono') or dazo.telefono
            dazo.horario = info.get('horario') or dazo.horario
            dazo.maps_url = info.get('maps_url') or dazo.maps_url
            dazo.foto_local_url = info.get('foto_local_url') or dazo.foto_local_url
    if not dazo.direccion:
        dazo.estado = 'incompleto'
    return dazo
