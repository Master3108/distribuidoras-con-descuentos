"""Publicador multicanal. Cada canal lee sus credenciales de variables de
entorno; si faltan, se omite con gracia (no rompe el flujo).

- Telegram:  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID            (foto local)
- WhatsApp:  WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, WHATSAPP_TO  (imagen por URL)
- Instagram: META_TOKEN, IG_USER_ID                          (imagen por URL)
- Facebook:  META_TOKEN, FB_PAGE_ID                          (imagen por URL)
- TikTok:    requiere aprobación de la Content Posting API → stub por ahora

Meta/IG/TikTok exigen aprobaciones de cuenta; mientras no estén, esos canales
simplemente se reportan como omitidos.
"""
import os
from typing import Optional

import httpx

from src.generador import _clp
from src.models import Dazo

GRAPH = 'https://graph.facebook.com/v21.0'
TIMEOUT = int(os.environ.get('PUBLICAR_TIMEOUT', '30'))


def construir_caption(dazo: Dazo) -> str:
    """Texto del post a partir del datazo."""
    lineas = [f'🔥 {dazo.producto}', f'💰 {_clp(dazo.precio_dazo)}']
    if dazo.precio_supermercado and dazo.ahorro_porcentaje:
        lineas.append(f'Antes {_clp(dazo.precio_supermercado)} — ahorras {dazo.ahorro_porcentaje}%')
    if dazo.local:
        loc = dazo.local + (f', {dazo.ubicacion_mencionada}' if dazo.ubicacion_mencionada else '')
        lineas.append(f'📍 {loc}')
    if dazo.direccion:
        lineas.append(dazo.direccion)
    if dazo.telefono:
        lineas.append(f'📞 {dazo.telefono}')
    if dazo.horario:
        lineas.append(f'🕐 {dazo.horario}')
    return '\n'.join(lineas)


def _omitido(canal: str) -> dict:
    return {'canal': canal, 'ok': False, 'motivo': 'sin credenciales'}


def publicar_telegram(dazo: Dazo, caption: str, imagen_path: Optional[str]) -> dict:
    tok, chat = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    if not tok or not chat:
        return _omitido('telegram')
    try:
        if imagen_path and os.path.exists(imagen_path):
            with open(imagen_path, 'rb') as f:
                r = httpx.post(f'https://api.telegram.org/bot{tok}/sendPhoto',
                               data={'chat_id': chat, 'caption': caption},
                               files={'photo': f}, timeout=TIMEOUT)
        else:
            r = httpx.post(f'https://api.telegram.org/bot{tok}/sendMessage',
                           data={'chat_id': chat, 'text': caption}, timeout=TIMEOUT)
        return {'canal': 'telegram', 'ok': bool(r.json().get('ok'))}
    except Exception as e:
        return {'canal': 'telegram', 'ok': False, 'error': str(e)}


def publicar_whatsapp(dazo: Dazo, caption: str, imagen_url: Optional[str]) -> dict:
    tok, phone, to = (os.environ.get('WHATSAPP_TOKEN'),
                      os.environ.get('WHATSAPP_PHONE_ID'), os.environ.get('WHATSAPP_TO'))
    if not (tok and phone and to and imagen_url):
        return _omitido('whatsapp')
    try:
        r = httpx.post(f'{GRAPH}/{phone}/messages',
                       headers={'Authorization': f'Bearer {tok}'},
                       json={'messaging_product': 'whatsapp', 'to': to, 'type': 'image',
                             'image': {'link': imagen_url, 'caption': caption}}, timeout=TIMEOUT)
        return {'canal': 'whatsapp', 'ok': r.status_code < 300}
    except Exception as e:
        return {'canal': 'whatsapp', 'ok': False, 'error': str(e)}


def publicar_facebook(dazo: Dazo, caption: str, imagen_url: Optional[str]) -> dict:
    tok, page = os.environ.get('META_TOKEN'), os.environ.get('FB_PAGE_ID')
    if not (tok and page and imagen_url):
        return _omitido('facebook')
    try:
        r = httpx.post(f'{GRAPH}/{page}/photos',
                       data={'url': imagen_url, 'caption': caption, 'access_token': tok}, timeout=TIMEOUT)
        return {'canal': 'facebook', 'ok': r.status_code < 300}
    except Exception as e:
        return {'canal': 'facebook', 'ok': False, 'error': str(e)}


def publicar_instagram(dazo: Dazo, caption: str, imagen_url: Optional[str]) -> dict:
    tok, iguser = os.environ.get('META_TOKEN'), os.environ.get('IG_USER_ID')
    if not (tok and iguser and imagen_url):
        return _omitido('instagram')
    try:
        # 1) crear contenedor, 2) publicarlo
        c = httpx.post(f'{GRAPH}/{iguser}/media',
                       data={'image_url': imagen_url, 'caption': caption, 'access_token': tok}, timeout=TIMEOUT)
        cid = c.json().get('id')
        if not cid:
            return {'canal': 'instagram', 'ok': False, 'error': 'sin container id'}
        p = httpx.post(f'{GRAPH}/{iguser}/media_publish',
                       data={'creation_id': cid, 'access_token': tok}, timeout=TIMEOUT)
        return {'canal': 'instagram', 'ok': p.status_code < 300}
    except Exception as e:
        return {'canal': 'instagram', 'ok': False, 'error': str(e)}


def publicar_tiktok(dazo: Dazo, caption: str, video_url: Optional[str]) -> dict:
    # La Content Posting API de TikTok requiere aprobación de la app + scopes.
    if not os.environ.get('TIKTOK_TOKEN'):
        return {'canal': 'tiktok', 'ok': False, 'motivo': 'requiere aprobación de API'}
    return {'canal': 'tiktok', 'ok': False, 'motivo': 'no implementado'}


def publicar_todos(dazo: Dazo, imagen_path: Optional[str] = None,
                   imagen_url: Optional[str] = None, video_url: Optional[str] = None) -> list[dict]:
    """Publica el datazo en todos los canales con credenciales disponibles.
    Devuelve la lista de resultados por canal."""
    caption = construir_caption(dazo)
    return [
        publicar_telegram(dazo, caption, imagen_path),
        publicar_whatsapp(dazo, caption, imagen_url),
        publicar_facebook(dazo, caption, imagen_url),
        publicar_instagram(dazo, caption, imagen_url),
        publicar_tiktok(dazo, caption, video_url),
    ]
