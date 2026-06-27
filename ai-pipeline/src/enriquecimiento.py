"""Enriquecimiento del local: dirección, teléfono, horario, Maps y foto.

Dos proveedores:
- Google Places API (v1): rico (teléfono, horario, foto). Requiere
  GOOGLE_MAPS_API_KEY (o GOOGLE_API_KEY con Places habilitado).
- OpenStreetMap / Nominatim: GRATIS y sin key. Da dirección + enlace a Maps
  (no teléfono ni horario). Es el fallback por defecto cuando no hay key.

Degrada con gracia: sin resultado devuelve None y el dazo queda 'incompleto'.
"""
import os
from typing import Optional

import httpx

PLACES_KEY = os.environ.get('GOOGLE_MAPS_API_KEY') or os.environ.get('GOOGLE_API_KEY')
ENABLED = os.environ.get('ENRIQUECIMIENTO_ENABLED', '1') not in ('0', 'false', 'False', '')
TIMEOUT = int(os.environ.get('ENRIQUECIMIENTO_TIMEOUT', '20'))
USER_AGENT = os.environ.get('NOMINATIM_UA', 'datazos-rm/1.0 (contacto@datazos.cl)')

# ─── Google Places (v1) ──────────────────────────────────────────────────────
_PLACES_URL = 'https://places.googleapis.com/v1/places:searchText'
_FIELD_MASK = ','.join([
    'places.displayName', 'places.formattedAddress', 'places.nationalPhoneNumber',
    'places.regularOpeningHours.weekdayDescriptions', 'places.googleMapsUri', 'places.photos',
])


def _foto_url(place: dict) -> Optional[str]:
    fotos = place.get('photos') or []
    if not fotos or not PLACES_KEY:
        return None
    return f"https://places.googleapis.com/v1/{fotos[0]['name']}/media?maxWidthPx=800&key={PLACES_KEY}"


def normalizar_lugar(place: dict) -> dict:
    """Normaliza un place de Google. Función pura (testeable)."""
    horas = (place.get('regularOpeningHours') or {}).get('weekdayDescriptions') or []
    return {
        'direccion': place.get('formattedAddress'),
        'telefono': place.get('nationalPhoneNumber'),
        'horario': '; '.join(horas) or None,
        'maps_url': place.get('googleMapsUri'),
        'foto_local_url': _foto_url(place),
    }


def _buscar_google(query: str) -> Optional[dict]:
    resp = httpx.post(
        _PLACES_URL,
        headers={'Content-Type': 'application/json', 'X-Goog-Api-Key': PLACES_KEY,
                 'X-Goog-FieldMask': _FIELD_MASK},
        json={'textQuery': query, 'languageCode': 'es', 'regionCode': 'CL', 'maxResultCount': 1},
        timeout=TIMEOUT,
    )
    places = (resp.json() or {}).get('places') or []
    return normalizar_lugar(places[0]) if places else None


# ─── OpenStreetMap / Nominatim (gratis, sin key) ─────────────────────────────
_NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'


def normalizar_osm(item: dict) -> dict:
    """Normaliza un resultado de Nominatim. Función pura (testeable)."""
    lat, lon = item.get('lat'), item.get('lon')
    maps_url = f'https://www.google.com/maps/search/?api=1&query={lat},{lon}' if lat and lon else None
    return {
        'direccion': item.get('display_name'),
        'telefono': None,   # Nominatim no entrega teléfono
        'horario': None,    # ni horario
        'maps_url': maps_url,
        'foto_local_url': None,
    }


def _buscar_osm(query: str) -> Optional[dict]:
    resp = httpx.get(
        _NOMINATIM_URL,
        params={'q': query, 'format': 'jsonv2', 'addressdetails': 1, 'limit': 1, 'countrycodes': 'cl'},
        headers={'User-Agent': USER_AGENT},
        timeout=TIMEOUT,
    )
    data = resp.json() or []
    return normalizar_osm(data[0]) if data else None


def buscar_local(nombre: str, comuna: Optional[str]) -> Optional[dict]:
    """Busca el local. Usa Google Places si hay key; si no, OpenStreetMap.
    Devuelve dict normalizado o None."""
    if not ENABLED or not nombre:
        return None
    query = ' '.join(filter(None, [nombre, comuna, 'Chile']))
    try:
        return _buscar_google(query) if PLACES_KEY else _buscar_osm(query)
    except Exception as e:
        print(f'  enriquecimiento: falló ({type(e).__name__})')
        return None
