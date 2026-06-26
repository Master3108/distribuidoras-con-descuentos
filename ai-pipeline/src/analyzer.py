import json
import os
import re

from google import genai
from google.genai import types
from src.models import VideoRecord, Dazo

VISION_MODEL = os.environ.get('GOOGLE_VISION_MODEL', 'gemini-2.0-flash')

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
    key = os.environ.get('GOOGLE_API_KEY')
    if not key or not frames:
        return []

    client = genai.Client(api_key=key)
    parts = []
    for frame_path in frames[:4]:
        if os.path.exists(frame_path):
            with open(frame_path, 'rb') as f:
                data = f.read()
            parts.append(types.Part.from_bytes(data=data, mime_type='image/jpeg'))

    parts.append(PROMPT_TEMPLATE.format(
        plataforma=video.plataforma,
        cuenta=video.cuenta,
        descripcion=video.descripcion[:300],
        url=video.url,
        transcript=transcript or '(sin audio disponible)',
    ))

    try:
        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=parts,
        )
        return parse_analysis_response(response.text, video)
    except Exception as e:
        print(f'  análisis Gemini falló: {e}')
        return []
