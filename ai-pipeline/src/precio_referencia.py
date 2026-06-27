"""Puente Python → extractor de precios (Node/Playwright).

El cerebro (Python) necesita el precio real de supermercado para calcular el
ahorro. El extractor vive en el proyecto Node `scrapening-ofertas` (Playwright +
stealth, ya probado). En vez de reescribirlo, lo llamamos como subproceso:

    node src/precio-referencia.js "<producto>" <mercado>   → imprime JSON

Incluye caché en disco (un precio de supermercado es estable por horas) para no
abrir un navegador en cada consulta, y degrada con gracia: si Node falla o no hay
coincidencia, devuelve None y el pipeline sigue con lo que tenga.
"""
import json
import os
import statistics
import subprocess
import time
from pathlib import Path
from typing import Optional

# Carpeta del proyecto Node con el extractor (por defecto, el hermano del repo).
SCRAPER_DIR = os.environ.get(
    'PRECIO_REFERENCIA_DIR',
    str(Path(__file__).resolve().parents[2] / 'scrapening-ofertas'),
)
# Supermercados a consultar para el precio de referencia (orden = preferencia).
# Default: los dos sin anti-bot duro (rápidos y estables).
MERCADOS = [m.strip() for m in os.environ.get('PRECIO_MERCADOS', 'jumbo,santaisabel').split(',') if m.strip()]
CACHE_TTL = int(os.environ.get('PRECIO_CACHE_TTL', '43200'))  # 12 h
CACHE_PATH = Path(os.environ.get('PRECIO_CACHE_PATH', str(Path(SCRAPER_DIR).parent / 'ai-pipeline' / '.precio_cache.json')))
TIMEOUT = int(os.environ.get('PRECIO_TIMEOUT', '90'))
ENABLED = os.environ.get('PRECIO_REFERENCIA_ENABLED', '1') not in ('0', 'false', 'False', '')


def _norm(nombre: str) -> str:
    return ' '.join((nombre or '').lower().split())


def _cache_load() -> dict:
    try:
        return json.loads(CACHE_PATH.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _cache_save(cache: dict) -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding='utf-8')
    except Exception:
        pass  # la caché es un lujo, nunca debe romper el pipeline


def _parse_stdout(stdout: str) -> Optional[dict]:
    """El CLI imprime JSON; extrae el objeto aunque haya ruido alrededor."""
    if not stdout:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        i, j = stdout.find('{'), stdout.rfind('}')
        if i >= 0 and j > i:
            try:
                return json.loads(stdout[i:j + 1])
            except json.JSONDecodeError:
                return None
    return None


def consultar_mercado(producto: str, mercado: str) -> Optional[dict]:
    """Lanza el extractor Node para un supermercado. Devuelve el mejor match
    ({nombre, marca, precio, ...}) o None si falla / no hay coincidencia."""
    try:
        proc = subprocess.run(
            ['node', 'src/precio-referencia.js', producto, mercado],
            cwd=SCRAPER_DIR,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f'  precio_referencia: {mercado} no disponible ({type(e).__name__})')
        return None
    data = _parse_stdout(proc.stdout)
    if not data:
        return None
    return data.get('mejor')


def precio_referencia(producto: str, mercados: Optional[list] = None) -> Optional[dict]:
    """Precio de referencia de supermercado para un producto.

    Consulta los mercados configurados, toma la mediana de los precios hallados
    (robusta ante outliers) y la devuelve junto al detalle por mercado.
    Cachea por nombre de producto. Devuelve None si no hay ningún precio.
    """
    if not ENABLED or not producto:
        return None
    mercados = mercados or MERCADOS
    clave = _norm(producto)

    cache = _cache_load()
    hit = cache.get(clave)
    if hit and (time.time() - hit.get('ts', 0)) < CACHE_TTL:
        return hit.get('valor')

    detalle = {}
    for mercado in mercados:
        mejor = consultar_mercado(producto, mercado)
        if mejor and mejor.get('precio'):
            detalle[mercado] = int(mejor['precio'])

    valor = None
    if detalle:
        valor = {
            'precio_referencia': round(statistics.median(detalle.values())),
            'detalle': detalle,
        }

    cache[clave] = {'ts': time.time(), 'valor': valor}
    _cache_save(cache)
    return valor
