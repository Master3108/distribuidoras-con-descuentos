import json
import os
import re
from google import genai
from google.genai import types
from src.models import VideoRecord, Dazo


PROMPT_TEMPLATE = """Analiza este contenido de redes sociales chilenas.

Plataforma: {plataforma}
Cuenta: {cuenta}
Descripción: {descripcion}
URL: {url}
Transcripción del audio: {transcript}

¿Este contenido muestra una distribuidora, almacén o supermercado en la Región Metropolitana de Chile vendiendo productos a precio de oferta ("datazo")?

Responde SOLO con JSON válido, sin texto adicional:
- Si NO es un dazo: {{"es_dazo": false, "razon": "motivo"}}
- Si SÍ es un dazo con uno o más productos, responde con un array JSON:
[
  {{
    "es_dazo": true,
    "producto": "nombre exacto del producto",
    "precio_dazo": 1000,
    "precio_supermercado": 3990,
    "ahorro_porcentaje": 75,
    "local": "nombre del local o null",
    "ubicacion_mencionada": "comuna o dirección o null"
  }}
]
Si no hay precio de referencia, usa null para precio_supermercado y ahorro_porcentaje."""


def parse_analysis_response(text: str, video: VideoRecord) -> list[Dazo]:
    """Parsea el JSON devuelto por Gemini. Devuelve lista de Dazo (puede ser vacía)."""
    text = re.sub(r'```(?:json)?\s*', '', text).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []

    if isinstance(parsed, dict):
        if not parsed.get('es_dazo', False):
            return []
        parsed = [parsed]

    datazos = []
    for item in parsed:
        if not item.get('es_dazo', False):
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
    """Envía frames + transcript a Gemini Vision. Devuelve lista de Dazo."""
    client = genai.Client(api_key=os.environ['GOOGLE_API_KEY'])

    parts = []
    for frame_path in frames:
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

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=parts,
    )
    return parse_analysis_response(response.text, video)
