import base64
import json
import os
import re

from src.models import VideoRecord, Dazo

# Visión con OpenAI (gpt-4o-mini por defecto). Se usa OpenAI porque es la key
# disponible; para cambiar a Gemini bastaría re-implementar este módulo + key.
VISION_MODEL = os.environ.get('OPENAI_VISION_MODEL', 'gpt-4o-mini')

PROMPT_TEMPLATE = """Analiza este contenido de redes sociales chilenas.

Plataforma: {plataforma}
Cuenta: {cuenta}
Descripción: {descripcion}
URL: {url}
Transcripción del audio: {transcript}

¿Muestra una distribuidora, almacén o supermercado en la Región Metropolitana de
Chile vendiendo productos a precio de oferta ("datazo")?

Responde SOLO con un objeto JSON válido:
- Si NO es un dazo: {{"es_dazo": false, "razon": "motivo"}}
- Si SÍ, lista cada producto en "datazos":
{{
  "datazos": [
    {{
      "producto": "nombre exacto del producto",
      "precio_dazo": 1000,
      "precio_supermercado": null,
      "ahorro_porcentaje": null,
      "local": "nombre del local o null",
      "ubicacion_mencionada": "comuna o dirección o null"
    }}
  ]
}}
Deja precio_supermercado y ahorro_porcentaje en null (se calculan después con datos reales)."""


def parse_analysis_response(text: str, video: VideoRecord) -> list[Dazo]:
    """Parsea el JSON del modelo. Tolera: objeto {datazos:[...]}, {es_dazo:false},
    un dazo suelto, o un array (formato heredado). Devuelve lista de Dazo."""
    text = re.sub(r'```(?:json)?\s*', '', text or '').strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []

    if isinstance(parsed, dict):
        if isinstance(parsed.get('datazos'), list):
            parsed = parsed['datazos']
        elif parsed.get('es_dazo') is False:
            return []
        else:
            parsed = [parsed]
    if not isinstance(parsed, list):
        return []

    datazos = []
    for item in parsed:
        if not isinstance(item, dict) or 'producto' not in item or item.get('precio_dazo') is None:
            continue
        datazos.append(Dazo(
            producto=item['producto'],
            precio_dazo=int(item['precio_dazo']),
            precio_supermercado=item.get('precio_supermercado'),
            ahorro_porcentaje=item.get('ahorro_porcentaje'),
            local=item.get('local'),
            ubicacion_mencionada=item.get('ubicacion_mencionada'),
            video_crudo_id=video.id,
            fuente_url=video.url,
            plataforma=video.plataforma,
            fecha_encontrado=video.fecha,
            foto_producto_url=None,
        ))
    return datazos


def analyze_video(frames: list[str], transcript: str, video: VideoRecord) -> list[Dazo]:
    """Envía frames + transcripción a OpenAI Vision. Devuelve lista de Dazo."""
    key = os.environ.get('OPENAI_API_KEY')
    if not key or not frames:
        return []
    from openai import OpenAI  # import lazy: el parser no requiere openai instalado
    client = OpenAI(api_key=key)

    content = [{'type': 'text', 'text': PROMPT_TEMPLATE.format(
        plataforma=video.plataforma, cuenta=video.cuenta,
        descripcion=video.descripcion[:300], url=video.url,
        transcript=transcript or '(sin audio disponible)',
    )}]
    for frame_path in frames[:4]:
        if os.path.exists(frame_path):
            with open(frame_path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode()
            content.append({'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}})

    try:
        resp = client.chat.completions.create(
            model=VISION_MODEL,
            temperature=0,
            response_format={'type': 'json_object'},
            messages=[{'role': 'user', 'content': content}],
        )
        return parse_analysis_response(resp.choices[0].message.content, video)
    except Exception as e:
        print(f'  análisis OpenAI falló: {e}')
        return []
