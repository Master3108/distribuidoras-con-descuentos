# Distribuidoras con Descuentos — Design Spec
**Fecha:** 2026-06-24

## Resumen

Sistema automatizado que monitorea redes sociales (TikTok, Instagram, YouTube, Facebook) buscando videos de distribuidoras, almacenes y supermercados de la Región Metropolitana de Chile con productos en oferta. Por cada producto encontrado extrae los datos con IA, enriquece la info buscando en internet, genera una imagen de marca y publica automáticamente en todos los canales (Instagram, TikTok, Facebook, WhatsApp, Telegram y sitio web).

**Objetivo:** Eliminar el trabajo manual de revisar redes sociales todo el día. El sistema lo hace solo y publica un post por producto encontrado, espaciado durante el día para maximizar el tiempo de permanencia en el perfil.

---

## Arquitectura General

```
Redes sociales (TikTok, IG, YT, FB)
        ↓
  [1] scrapening-ofertas (Apify Actor)
        ↓
  [2] Filtro IA (Claude Vision + Whisper)
        ↓
  [3] Enriquecimiento Web (Google APIs)
        ↓
  [4] Generador de Contenido (Pillow + FFmpeg)
        ↓
  [5] Publicador Multi-Canal
        ↓
Instagram · TikTok · Facebook · WhatsApp · Telegram · Web
```

---

## Módulo 1: scrapening-ofertas (Apify Actor)

**Tecnología:** Node.js + Playwright, desplegado en Apify Cloud. Clonado desde un actor open-source existente y adaptado.

**Fuentes monitoreadas:**

Cuentas conocidas (lista configurable):
- TikTok, Instagram, YouTube, Facebook de cuentas conocidas de distribuidoras y creadores de contenido de datazos.

Búsqueda por hashtags/keywords:
- `#datazo`, `#distribuidora`, `#santiago`, `#RM`, `#oferta`, `#chile`, `#descuento`, `#maipú`, `#pudahuel`, etc.

Fuentes por tipo:
- Distribuidoras y almacenes de la RM
- Supermercados: Lider, Jumbo, Santa Isabel, Unimarc, Acuenta y otros

**Output por video encontrado:**
```json
{
  "url": "https://tiktok.com/...",
  "plataforma": "tiktok",
  "cuenta": "@matsi_matsi",
  "descripcion": "Datazo de mantequilla...",
  "fecha": "2026-06-24",
  "miniatura_url": "...",
  "video_url": "..."
}
```

**Ejecución:** Scheduler de Apify, 3 veces al día. Guarda el último ID procesado por plataforma para no repetir contenido.

---

## Módulo 2: Filtro IA + Extracción de Datos

**Tecnología:** Python. Whisper (OpenAI) para transcripción de audio. Claude Vision para análisis de imagen/video.

**Proceso:**
1. Descarga miniatura y extrae frames clave del video con FFmpeg.
2. Transcribe el audio con Whisper.
3. Envía frames + transcripción a Claude Vision con el prompt de análisis.

**Prompt de análisis:**
> ¿Este video muestra una distribuidora, almacén o supermercado en la Región Metropolitana de Chile vendiendo un producto a precio de oferta?
> Si sí → extrae: nombre del producto, precio oferta (CLP), nombre del local, ubicación mencionada, precio de referencia en supermercado si aparece.
> Si no → descarta con razón.

**Output válido (un objeto por producto detectado):**
```json
{
  "es_dazo": true,
  "producto": "Mantequilla Sin Lactosa Quillayes",
  "precio_dazo": 1000,
  "precio_supermercado": 3990,
  "ahorro_porcentaje": 75,
  "local": "Distribuidora Quillayes",
  "ubicacion_mencionada": "Maipú",
  "frame_capturado_url": "..."
}
```

Un video con 4 productos genera 4 objetos independientes → 4 posts separados.

**Output inválido:**
```json
{
  "es_dazo": false,
  "razon": "No es de la RM"
}
```

---

## Módulo 3: Enriquecimiento Web

**Tecnología:** Python. Google Custom Search API + Google Maps API.

**Qué busca con el nombre del local + ubicación:**
- Dirección exacta
- Teléfono / WhatsApp de contacto
- Horario de atención
- Fotos del local (Google Maps)
- Sitio web o Instagram oficial

**Output:**
```json
{
  "direccion": "Av. 5 de Abril 1234, Maipú",
  "telefono": "+56 9 1234 5678",
  "horario": "Lun-Sáb 8:00-18:00",
  "foto_local_url": "...",
  "maps_url": "https://maps.google.com/..."
}
```

Si no encuentra info suficiente: el dazo se guarda en base de datos con estado `incompleto` sin publicar automáticamente.

---

## Módulo 4: Generador de Contenido

**Tecnología:** Python + Pillow (imágenes) + FFmpeg (video animado).

**Regla principal:** Un producto = un post. Máximo engagement por unidad de contenido.

**Foto del producto:** Primero usa el frame capturado directamente del video original. Si no es suficientemente claro, complementa con búsqueda de imagen en internet.

**Formatos generados:**
- Historia/Story (1080×1920) → Instagram, Facebook, TikTok
- Post cuadrado (1080×1080) → Instagram feed, Facebook feed
- Imagen horizontal (1280×720) → Sitio web
- Video corto animado (5-8 seg, FFmpeg) → TikTok, Reels

**Layout de plantilla:**
```
┌─────────────────────────────┐
│  🔥 DAZO DEL DÍA            │
│                             │
│  [FOTO PRODUCTO]            │
│                             │
│  Mantequilla Sin Lactosa    │
│  ─────────────────────────  │
│  💰 $1.000    ~~$3.990~~    │
│      AHORRAS UN 75%         │
│                             │
│  📍 Distrib. Quillayes      │
│     Av. 5 de Abril, Maipú  │
│  📞 +56 9 1234 5678         │
│  🕐 Lun-Sáb 8:00-18:00     │
│                             │
│  [LOGO MARCA]               │
└─────────────────────────────┘
```

Paleta de colores, fuentes y logo definidos una sola vez como variables de plantilla. Identidad visual consistente en todos los posts.

---

## Módulo 5: Publicador Multi-Canal

**Tecnología:** Python. APIs oficiales de cada plataforma.

| Canal | API | Formato |
|---|---|---|
| Instagram | Meta Graph API | Post feed + Historia |
| Facebook | Meta Graph API | Post + Historia + Reel |
| TikTok | TikTok Content Posting API | Video animado |
| WhatsApp | WhatsApp Business API | Imagen + texto |
| Telegram | Telegram Bot API | Imagen + texto (canal público) |
| Sitio web | Supabase (insert) | Guardado en BD |

**Lógica de publicación espaciada:**

Los productos encontrados en el día se ordenan por porcentaje de ahorro (mayor ahorro primero) y se publican con intervalos:

```
08:00 → Post 1 (mayor ahorro)
11:00 → Post 2
14:00 → Post 3
17:00 → Post 4
20:00 → Post 5
(continúa según volumen del día)
```

---

## Sitio Web (Next.js + Supabase)

Archivo consultable de todos los datazos encontrados.

**Filtros disponibles:**
- Categoría de producto (lácteos, carnes, verduras, etc.)
- Comuna (Maipú, Pudahuel, Santiago, etc.)
- Tipo de local (distribuidora vs supermercado)
- Buscador por nombre de producto

**Cada dazo muestra:** foto producto, precio oferta, precio referencia supermercado, % ahorro, nombre local, dirección, teléfono, horario, enlace a Google Maps.

---

## Base de Datos (Supabase / PostgreSQL)

Tablas principales:

**`datazos`**
- id, producto, precio_dazo, precio_supermercado, ahorro_porcentaje
- local, direccion, telefono, horario, maps_url
- foto_producto_url, foto_local_url
- fuente_url, plataforma, fecha_encontrado
- estado: `pendiente` | `publicado` | `incompleto`

**`cuentas_monitoreadas`**
- id, plataforma, handle, activa, ultima_revision

**`publicaciones`**
- id, dazo_id, canal, fecha_publicacion, url_publicacion

---

## Stack Tecnológico Completo

| Componente | Tecnología |
|---|---|
| Scraper | Apify Actor "scrapening-ofertas" (Node.js + Playwright) |
| Transcripción audio | Whisper (OpenAI) |
| Análisis IA | Claude Vision |
| Enriquecimiento | Google Custom Search API + Google Maps API |
| Extracción frames | FFmpeg |
| Generación imágenes | Python + Pillow |
| Generación video | FFmpeg |
| Publicación social | Meta Graph API, TikTok API, WhatsApp Business API, Telegram Bot API |
| Base de datos | Supabase (PostgreSQL) |
| Sitio web | Next.js |
| Scheduler | Apify Scheduler + cron en servidor |
| Servidor backend | Python (FastAPI o scripts cron) |

---

## Flujo Completo Resumido

```
3x/día (cron):
  scrapening-ofertas corre en Apify
  → Lista de videos nuevos

Por cada video:
  Whisper transcribe audio
  Claude Vision analiza frames + transcripción
  → Si es dazo: extrae producto(s)

Por cada producto:
  Google APIs buscan info del local
  FFmpeg captura mejor frame del video
  Pillow genera imagen de marca
  FFmpeg genera video animado

Según horario del día:
  Meta API publica en Instagram + Facebook
  TikTok API publica video
  WhatsApp Business envía al canal
  Telegram Bot envía al canal
  Supabase guarda en BD → aparece en web
```
