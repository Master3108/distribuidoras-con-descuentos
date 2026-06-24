# AI Pipeline — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pipeline Python que lee videos sin procesar de Supabase, los analiza con Claude Vision + Whisper, y guarda cada producto encontrado como un "dazo" en la tabla `datazos`.

**Architecture:** Script Python que se ejecuta como cron en el VPS. Lee `videos_crudos` donde `procesado=false`, descarga la miniatura, opcionalmente transcribe el audio con OpenAI Whisper, y envía frames + transcripción a Claude Vision para extraer productos con precio. Un video con 4 productos genera 4 filas en `datazos`.

**Tech Stack:** Python 3.11, anthropic SDK, openai SDK (Whisper), supabase-py, httpx, Pillow, pytest, python-dotenv.

---

## Estructura de archivos

```
ai-pipeline/
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── .env.example
├── src/
│   ├── __init__.py
│   ├── models.py          — dataclasses VideoRecord y Dazo + calcular_ahorro()
│   ├── storage.py         — Supabase: leer videos_crudos, escribir datazos, subir frames
│   ├── downloader.py      — descarga thumbnail/video por URL con httpx
│   ├── extractor.py       — extrae frames de video con FFmpeg (subprocess)
│   ├── transcriber.py     — transcribe audio con OpenAI Whisper API
│   ├── analyzer.py        — Claude Vision: frames + transcript → list[Dazo]
│   └── main.py            — orquestador: lee N videos, corre pipeline, marca procesado
├── supabase/
│   └── migrations/
│       └── 002_datazos.sql
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_extractor.py
    └── test_analyzer.py
```

---

### Task 1: Setup del proyecto Python

**Files:**
- Create: `ai-pipeline/requirements.txt`
- Create: `ai-pipeline/requirements-dev.txt`
- Create: `ai-pipeline/pytest.ini`
- Create: `ai-pipeline/.env.example`
- Create: `ai-pipeline/src/__init__.py`
- Create: `ai-pipeline/tests/__init__.py`

- [ ] **Step 1: Crear `requirements.txt`**

```
anthropic>=0.40.0
openai>=1.50.0
supabase>=2.0.0
httpx>=0.27.0
python-dotenv>=1.0.0
Pillow>=10.0.0
```

- [ ] **Step 2: Crear `requirements-dev.txt`**

```
pytest>=8.0.0
pytest-mock>=3.12.0
```

- [ ] **Step 3: Crear `pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

- [ ] **Step 4: Crear `.env.example`**

```
# Supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# Anthropic (Claude Vision)
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI (Whisper)
OPENAI_API_KEY=sk-...

# Pipeline config
BATCH_SIZE=10
```

- [ ] **Step 5: Crear archivos `__init__.py` vacíos**

```bash
# Bash
mkdir -p ai-pipeline/src ai-pipeline/tests ai-pipeline/supabase/migrations
touch ai-pipeline/src/__init__.py ai-pipeline/tests/__init__.py
```

- [ ] **Step 6: Commit**

```bash
git add ai-pipeline/
git commit -m "feat: setup proyecto ai-pipeline Python"
```

---

### Task 2: Migración DB — tabla datazos

**Files:**
- Create: `ai-pipeline/supabase/migrations/002_datazos.sql`

- [ ] **Step 1: Crear `supabase/migrations/002_datazos.sql`**

```sql
CREATE TABLE IF NOT EXISTS datazos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

    -- Extraído por Claude Vision
    producto TEXT NOT NULL,
    precio_dazo INTEGER NOT NULL,
    precio_supermercado INTEGER,
    ahorro_porcentaje INTEGER,
    local TEXT,
    ubicacion_mencionada TEXT,

    -- Foto del producto (frame capturado o thumbnail)
    foto_producto_url TEXT,

    -- Enriquecimiento web (Plan 3 — vacíos por ahora)
    direccion TEXT,
    telefono TEXT,
    horario TEXT,
    maps_url TEXT,
    foto_local_url TEXT,

    -- Trazabilidad a la fuente
    video_crudo_id TEXT REFERENCES videos_crudos(id),
    fuente_url TEXT,
    plataforma TEXT,
    fecha_encontrado DATE,

    -- Estado del flujo de publicación
    estado TEXT DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente', 'publicado', 'incompleto')),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_datazos_estado ON datazos(estado);
CREATE INDEX IF NOT EXISTS idx_datazos_fecha ON datazos(fecha_encontrado DESC);
CREATE INDEX IF NOT EXISTS idx_datazos_video ON datazos(video_crudo_id);
```

- [ ] **Step 2: Commit**

```bash
git add ai-pipeline/supabase/migrations/002_datazos.sql
git commit -m "feat: migración SQL tabla datazos"
```

---

### Task 3: Modelos de datos (models.py)

**Files:**
- Create: `ai-pipeline/src/models.py`
- Test: `ai-pipeline/tests/test_models.py`

- [ ] **Step 1: Escribir tests que fallan**

```python
# tests/test_models.py
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
```

- [ ] **Step 2: Correr tests — deben fallar**

```bash
cd ai-pipeline && python -m pytest tests/test_models.py -v
```
Expected: `ModuleNotFoundError: No module named 'src.models'`

- [ ] **Step 3: Crear `src/models.py`**

```python
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
```

- [ ] **Step 4: Correr tests — deben pasar**

```bash
cd ai-pipeline && python -m pytest tests/test_models.py -v
```
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add ai-pipeline/src/models.py ai-pipeline/tests/test_models.py
git commit -m "feat: modelos de datos VideoRecord y Dazo"
```

---

### Task 4: Storage Supabase (storage.py)

**Files:**
- Create: `ai-pipeline/src/storage.py`

No hay tests unitarios para storage.py — todas sus funciones son I/O puro contra Supabase. Se verifica en integración al correr main.py.

- [ ] **Step 1: Crear `src/storage.py`**

```python
import os
from supabase import create_client, Client
from src.models import VideoRecord, Dazo

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(
            os.environ['SUPABASE_URL'],
            os.environ['SUPABASE_SERVICE_KEY'],
        )
    return _client


def fetch_unprocessed_videos(limit: int = 10) -> list[VideoRecord]:
    res = _get_client().table('videos_crudos') \
        .select('*') \
        .eq('procesado', False) \
        .order('fecha_encontrado', desc=False) \
        .limit(limit) \
        .execute()
    return [VideoRecord(**row) for row in res.data]


def mark_video_processed(video_id: str) -> None:
    _get_client().table('videos_crudos') \
        .update({'procesado': True}) \
        .eq('id', video_id) \
        .execute()


def save_dazo(dazo: Dazo) -> None:
    row = {
        'producto': dazo.producto,
        'precio_dazo': dazo.precio_dazo,
        'precio_supermercado': dazo.precio_supermercado,
        'ahorro_porcentaje': dazo.ahorro_porcentaje,
        'local': dazo.local,
        'ubicacion_mencionada': dazo.ubicacion_mencionada,
        'foto_producto_url': dazo.foto_producto_url,
        'video_crudo_id': dazo.video_crudo_id,
        'fuente_url': dazo.fuente_url,
        'plataforma': dazo.plataforma,
        'fecha_encontrado': dazo.fecha_encontrado,
        'estado': 'pendiente',
    }
    _get_client().table('datazos').insert(row).execute()


def upload_frame(image_bytes: bytes, filename: str) -> str:
    """Sube imagen a Supabase Storage y devuelve URL pública."""
    bucket = 'datazos-frames'
    client = _get_client()
    client.storage.from_(bucket).upload(
        path=filename,
        file=image_bytes,
        file_options={'content-type': 'image/jpeg', 'upsert': 'true'},
    )
    res = client.storage.from_(bucket).get_public_url(filename)
    return res
```

- [ ] **Step 2: Commit**

```bash
git add ai-pipeline/src/storage.py
git commit -m "feat: storage Supabase para videos_crudos y datazos"
```

---

### Task 5: Downloader (downloader.py)

**Files:**
- Create: `ai-pipeline/src/downloader.py`

No tests unitarios — descarga URLs externas. Se verifica en integración.

- [ ] **Step 1: Crear `src/downloader.py`**

```python
import httpx
import tempfile
import os
from pathlib import Path


def download_to_temp(url: str, suffix: str = '.jpg') -> str | None:
    """Descarga URL a archivo temporal. Devuelve ruta o None si falla."""
    if not url:
        return None
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(response.content)
        tmp.close()
        return tmp.name
    except Exception as e:
        print(f'Download failed for {url}: {e}')
        return None


def download_thumbnail(url: str) -> str | None:
    return download_to_temp(url, suffix='.jpg')


def download_video(url: str) -> str | None:
    return download_to_temp(url, suffix='.mp4')


def cleanup(path: str | None) -> None:
    if path and os.path.exists(path):
        os.unlink(path)
```

- [ ] **Step 2: Commit**

```bash
git add ai-pipeline/src/downloader.py
git commit -m "feat: downloader de thumbnails y videos"
```

---

### Task 6: Extractor de frames FFmpeg (extractor.py)

**Files:**
- Create: `ai-pipeline/src/extractor.py`
- Test: `ai-pipeline/tests/test_extractor.py`

- [ ] **Step 1: Escribir tests que fallan**

```python
# tests/test_extractor.py
import os
import tempfile
from PIL import Image
from src.extractor import frames_from_image, frames_from_video


def test_frames_from_image_devuelve_lista_con_la_imagen():
    # Crea imagen temporal de 100x100 px
    img = Image.new('RGB', (100, 100), color=(255, 0, 0))
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        img.save(f.name)
        path = f.name
    try:
        result = frames_from_image(path)
        assert len(result) == 1
        assert result[0] == path
    finally:
        os.unlink(path)


def test_frames_from_video_devuelve_lista_vacia_si_ffmpeg_falla():
    result = frames_from_video('/archivo/no/existe.mp4', num_frames=3)
    assert result == []
```

- [ ] **Step 2: Correr tests — deben fallar**

```bash
cd ai-pipeline && python -m pytest tests/test_extractor.py -v
```
Expected: `ModuleNotFoundError: No module named 'src.extractor'`

- [ ] **Step 3: Crear `src/extractor.py`**

```python
import subprocess
import tempfile
import os


def frames_from_image(image_path: str) -> list[str]:
    """Wrapper para imágenes estáticas — devuelve [image_path] directamente."""
    return [image_path]


def frames_from_video(video_path: str, num_frames: int = 5) -> list[str]:
    """Extrae num_frames fotogramas equidistantes del video con FFmpeg.
    Devuelve lista de rutas temporales o [] si FFmpeg falla."""
    if not os.path.exists(video_path):
        return []

    tmp_dir = tempfile.mkdtemp()
    output_pattern = os.path.join(tmp_dir, 'frame_%03d.jpg')

    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', f'fps=1/5,select=not(mod(n\\,{max(1, num_frames)}))',
        '-frames:v', str(num_frames),
        '-q:v', '2',
        output_pattern,
        '-y', '-loglevel', 'error',
    ]

    try:
        subprocess.run(cmd, check=True, timeout=60)
        frames = sorted([
            os.path.join(tmp_dir, f)
            for f in os.listdir(tmp_dir)
            if f.endswith('.jpg')
        ])
        return frames[:num_frames]
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return []
```

- [ ] **Step 4: Instalar Pillow para tests**

```bash
cd ai-pipeline && pip install Pillow
```

- [ ] **Step 5: Correr tests — deben pasar**

```bash
cd ai-pipeline && python -m pytest tests/test_extractor.py -v
```
Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add ai-pipeline/src/extractor.py ai-pipeline/tests/test_extractor.py
git commit -m "feat: extractor de frames FFmpeg"
```

---

### Task 7: Transcriptor Whisper (transcriber.py)

**Files:**
- Create: `ai-pipeline/src/transcriber.py`

No tests unitarios — llama a OpenAI API. Se verifica en integración.

- [ ] **Step 1: Crear `src/transcriber.py`**

```python
import os
import openai


def transcribe_audio(video_path: str) -> str:
    """Transcribe el audio del video con OpenAI Whisper API.
    Devuelve string vacío si falla o no hay audio."""
    if not video_path or not os.path.exists(video_path):
        return ''
    try:
        client = openai.OpenAI(api_key=os.environ['OPENAI_API_KEY'])
        with open(video_path, 'rb') as f:
            result = client.audio.transcriptions.create(
                model='whisper-1',
                file=f,
                language='es',
            )
        return result.text
    except Exception as e:
        print(f'Whisper transcription failed: {e}')
        return ''
```

- [ ] **Step 2: Commit**

```bash
git add ai-pipeline/src/transcriber.py
git commit -m "feat: transcriptor de audio con OpenAI Whisper"
```

---

### Task 8: Analizador Claude Vision (analyzer.py)

**Files:**
- Create: `ai-pipeline/src/analyzer.py`
- Test: `ai-pipeline/tests/test_analyzer.py`

- [ ] **Step 1: Escribir tests que fallan**

```python
# tests/test_analyzer.py
from src.analyzer import parse_analysis_response
from src.models import VideoRecord


def _make_video(id='v1', plataforma='tiktok'):
    return VideoRecord(
        id=id, url='https://tiktok.com/v/1', plataforma=plataforma,
        cuenta='@test', descripcion='datazo mantequilla',
        fecha='2026-06-24', miniatura_url='', video_url='',
    )


def test_parse_respuesta_no_es_dazo():
    json_str = '{"es_dazo": false, "razon": "No es de la RM"}'
    result = parse_analysis_response(json_str, _make_video())
    assert result == []


def test_parse_respuesta_un_producto():
    json_str = '''[{
        "es_dazo": true,
        "producto": "Mantequilla Quillayes",
        "precio_dazo": 1000,
        "precio_supermercado": 3990,
        "ahorro_porcentaje": 75,
        "local": "Distribuidora Quillayes",
        "ubicacion_mencionada": "Maipú"
    }]'''
    result = parse_analysis_response(json_str, _make_video())
    assert len(result) == 1
    assert result[0].producto == 'Mantequilla Quillayes'
    assert result[0].precio_dazo == 1000
    assert result[0].plataforma == 'tiktok'
    assert result[0].video_crudo_id == 'v1'


def test_parse_respuesta_multiples_productos():
    json_str = '''[
        {"es_dazo": true, "producto": "Leche", "precio_dazo": 500,
         "precio_supermercado": 900, "ahorro_porcentaje": 44,
         "local": "Distrib X", "ubicacion_mencionada": "Santiago"},
        {"es_dazo": true, "producto": "Yogur", "precio_dazo": 300,
         "precio_supermercado": 700, "ahorro_porcentaje": 57,
         "local": "Distrib X", "ubicacion_mencionada": "Santiago"}
    ]'''
    result = parse_analysis_response(json_str, _make_video())
    assert len(result) == 2
    assert result[1].producto == 'Yogur'


def test_parse_respuesta_json_invalido_devuelve_vacio():
    result = parse_analysis_response('no es json', _make_video())
    assert result == []


def test_parse_respuesta_con_bloque_markdown():
    json_str = '```json\n[{"es_dazo": true, "producto": "Aceite", "precio_dazo": 2000, "precio_supermercado": null, "ahorro_porcentaje": null, "local": null, "ubicacion_mencionada": null}]\n```'
    result = parse_analysis_response(json_str, _make_video())
    assert len(result) == 1
    assert result[0].producto == 'Aceite'
```

- [ ] **Step 2: Correr tests — deben fallar**

```bash
cd ai-pipeline && python -m pytest tests/test_analyzer.py -v
```
Expected: `ModuleNotFoundError: No module named 'src.analyzer'`

- [ ] **Step 3: Crear `src/analyzer.py`**

```python
import base64
import json
import os
import re
import anthropic
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


def _encode_image(path: str) -> dict:
    with open(path, 'rb') as f:
        data = base64.standard_b64encode(f.read()).decode('utf-8')
    return {
        'type': 'image',
        'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': data},
    }


def parse_analysis_response(text: str, video: VideoRecord) -> list[Dazo]:
    """Parsea el JSON devuelto por Claude. Devuelve lista de Dazo (puede ser vacía)."""
    # Quitar bloques markdown si los hay
    text = re.sub(r'```(?:json)?\s*', '', text).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []

    # Caso: objeto único con es_dazo: false
    if isinstance(parsed, dict):
        if not parsed.get('es_dazo', False):
            return []
        parsed = [parsed]

    # Caso: array de productos
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
    """Envía frames + transcript a Claude Vision. Devuelve lista de Dazo."""
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

    content = [_encode_image(f) for f in frames if os.path.exists(f)]
    content.append({'type': 'text', 'text': PROMPT_TEMPLATE.format(
        plataforma=video.plataforma,
        cuenta=video.cuenta,
        descripcion=video.descripcion[:300],
        url=video.url,
        transcript=transcript or '(sin audio disponible)',
    )})

    response = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=2000,
        messages=[{'role': 'user', 'content': content}],
    )
    return parse_analysis_response(response.content[0].text, video)
```

- [ ] **Step 4: Correr tests — deben pasar**

```bash
cd ai-pipeline && python -m pytest tests/test_analyzer.py -v
```
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add ai-pipeline/src/analyzer.py ai-pipeline/tests/test_analyzer.py
git commit -m "feat: analizador Claude Vision con parser de respuesta"
```

---

### Task 9: Orquestador principal (main.py)

**Files:**
- Create: `ai-pipeline/src/main.py`

No tests unitarios — orquesta I/O. Se verifica ejecutando con `BATCH_SIZE=1` y un video real en Supabase.

- [ ] **Step 1: Crear `src/main.py`**

```python
import os
import dotenv
dotenv.load_dotenv()

from src.models import VideoRecord
from src.storage import fetch_unprocessed_videos, mark_video_processed, save_dazo, upload_frame
from src.downloader import download_thumbnail, download_video, cleanup
from src.extractor import frames_from_image, frames_from_video
from src.transcriber import transcribe_audio
from src.analyzer import analyze_video

BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '10'))


def process_video(video: VideoRecord) -> int:
    """Procesa un video. Devuelve número de datazos encontrados."""
    tmp_thumbnail = None
    tmp_video = None
    extra_frames = []
    datazos_count = 0

    try:
        # 1. Descargar thumbnail (siempre disponible)
        tmp_thumbnail = download_thumbnail(video.miniatura_url)
        frames = frames_from_image(tmp_thumbnail) if tmp_thumbnail else []

        # 2. Intentar descargar video para frames adicionales + audio
        transcript = ''
        tmp_video = download_video(video.video_url)
        if tmp_video:
            extra_frames = frames_from_video(tmp_video, num_frames=4)
            if extra_frames:
                frames = extra_frames
            transcript = transcribe_audio(tmp_video)

        if not frames:
            print(f'  Sin frames para {video.id} — saltando')
            return 0

        # 3. Analizar con Claude Vision
        datazos = analyze_video(frames, transcript, video)

        # 4. Subir foto del producto y guardar cada dazo
        for dazo in datazos:
            foto_url = None
            if frames:
                with open(frames[0], 'rb') as f:
                    foto_url = upload_frame(f.read(), f'dazo_{video.id}_{dazo.producto[:20]}.jpg')
            dazo.foto_producto_url = foto_url
            save_dazo(dazo)
            datazos_count += 1
            print(f'  ✅ Dazo: {dazo.producto} ${dazo.precio_dazo:,} — {dazo.local}')

    except Exception as e:
        print(f'  Error procesando {video.id}: {e}')

    finally:
        cleanup(tmp_thumbnail)
        cleanup(tmp_video)
        for f in extra_frames:
            cleanup(f)

    return datazos_count


def main():
    print(f'ai-pipeline iniciando — batch size: {BATCH_SIZE}')
    videos = fetch_unprocessed_videos(limit=BATCH_SIZE)
    print(f'{len(videos)} videos sin procesar encontrados')

    total_datazos = 0
    for i, video in enumerate(videos, 1):
        print(f'[{i}/{len(videos)}] {video.plataforma} {video.cuenta} — {video.id}')
        count = process_video(video)
        mark_video_processed(video.id)
        total_datazos += count

    print(f'\n✅ ai-pipeline completado. {total_datazos} datazos extraídos de {len(videos)} videos.')


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Commit**

```bash
git add ai-pipeline/src/main.py
git commit -m "feat: orquestador principal ai-pipeline"
```

---

### Task 10: Deploy en VPS

**Files:**
- Create: `ai-pipeline/deploy/setup-vps.sh`
- Modify: `scrapening-ofertas/deploy/cron-setup.sh` — agregar cron para ai-pipeline

- [ ] **Step 1: Crear `deploy/setup-vps.sh`**

```bash
#!/bin/bash
# Setup ai-pipeline en VPS
set -e

cd /opt/distribuidoras/ai-pipeline

# Instalar dependencias del sistema
apt-get install -y python3.11 python3.11-pip python3.11-venv ffmpeg

# Crear virtualenv
python3.11 -m venv .venv
source .venv/bin/activate

# Instalar dependencias Python
pip install -r requirements.txt

# Copiar .env si no existe
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Edita /opt/distribuidoras/ai-pipeline/.env con tus credenciales"
fi

echo "✅ ai-pipeline instalado"
```

- [ ] **Step 2: Añadir cron para ai-pipeline (30 min después del scraper)**

El scraper corre a 8:00, 13:00, 19:00. El pipeline AI corre a 8:30, 13:30, 19:30 para que ya haya datos nuevos.

```bash
# Añadir manualmente al crontab del VPS:
# 30 8,13,19 * * * cd /opt/distribuidoras/ai-pipeline && .venv/bin/python src/main.py >> /var/log/ai-pipeline.log 2>&1
```

- [ ] **Step 3: Aplicar migración SQL en Supabase**

Ir a Supabase → SQL Editor → ejecutar el contenido de:
`ai-pipeline/supabase/migrations/002_datazos.sql`

También crear el bucket en Supabase Storage → New Bucket → nombre: `datazos-frames` → Public.

- [ ] **Step 4: Test de integración manual**

```bash
cd /opt/distribuidoras/ai-pipeline
source .venv/bin/activate
BATCH_SIZE=1 python src/main.py
```

Verificar en Supabase Table Editor que aparece una fila en `datazos`.

- [ ] **Step 5: Commit**

```bash
git add ai-pipeline/deploy/setup-vps.sh
git commit -m "feat: scripts de deploy VPS para ai-pipeline"
```

---

## Self-Review

### 1. Spec coverage

| Req del spec | Task |
|---|---|
| Descargar miniatura | Task 5 (downloader.py) + Task 6 (extractor.py) |
| Extraer frames con FFmpeg | Task 6 (extractor.py) |
| Transcribir audio con Whisper | Task 7 (transcriber.py) |
| Enviar a Claude Vision | Task 8 (analyzer.py) |
| Un video → N objetos separados | Task 8 + Task 9 (loop sobre datazos) |
| Output con es_dazo: false | Task 8 (parse_analysis_response) |
| Guardar en tabla datazos | Task 2 (SQL) + Task 4 (storage.py) |
| estado: pendiente/publicado/incompleto | Task 2 (SQL CHECK constraint) |
| frame_capturado_url | Task 9 (upload_frame → dazo.foto_producto_url) |
| Deploy en VPS + cron | Task 10 |

### 2. Placeholder scan
Ninguno encontrado — cada task tiene código completo.

### 3. Type consistency
- `VideoRecord` definido en Task 3, usado en Tasks 4, 8, 9 — consistente.
- `Dazo` definido en Task 3, creado en Task 8, guardado en Task 4 — consistente.
- `calcular_ahorro()` definido en Task 3, no se llama en otros tasks (el ahorro lo calcula Claude directamente del video, pero se expone para tests).
- `frames_from_image` / `frames_from_video` definidos en Task 6, usados en Task 9 — consistente.
- `upload_frame(bytes, filename)` definido en Task 4, llamado en Task 9 — consistente.
