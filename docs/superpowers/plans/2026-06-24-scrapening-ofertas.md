# scrapening-ofertas — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir "scrapening-ofertas", un Apify Actor que scraping TikTok, Instagram, YouTube y Facebook buscando videos de distribuidoras y supermercados de la Región Metropolitana de Chile con productos en oferta, y entrega los resultados como dataset para el pipeline de IA.

**Architecture:** El actor corre en Apify Cloud con scheduler (3 veces/día). Itera sobre cuentas conocidas y hashtags/keywords por plataforma, scraping solo contenido nuevo (deduplicación vía Apify KV Store), y pushea resultados al Apify Dataset. TikTok e Instagram usan Playwright con proxies de Apify. YouTube usa la API oficial (Data API v3). Facebook usa Playwright sobre páginas públicas.

**Tech Stack:** Node.js 18, Apify SDK v3, Playwright, YouTube Data API v3, Jest

---

## Estructura de Archivos

```
scrapening-ofertas/
├── .actor/
│   ├── actor.json           # metadata del actor (nombre, versión, build)
│   └── input_schema.json    # esquema de inputs del actor
├── src/
│   ├── main.js              # entry point: orquesta todos los scrapers
│   ├── config.js            # hashtags por defecto, constantes
│   ├── dedup.js             # deduplicación con Apify KV Store
│   ├── scrapers/
│   │   ├── tiktok.js        # scraper TikTok (Playwright)
│   │   ├── instagram.js     # scraper Instagram (Playwright)
│   │   ├── youtube.js       # scraper YouTube (API v3)
│   │   └── facebook.js      # scraper Facebook (Playwright)
│   └── browser.js           # utilidades Playwright compartidas
├── tests/
│   ├── dedup.test.js
│   ├── config.test.js
│   └── scrapers/
│       └── youtube.test.js  # youtube es el único testeable sin browser
├── package.json
└── .env.example             # variables de entorno requeridas
```

---

## Task 1: Setup del proyecto Apify Actor

**Files:**
- Create: `scrapening-ofertas/package.json`
- Create: `scrapening-ofertas/.actor/actor.json`
- Create: `scrapening-ofertas/.actor/input_schema.json`
- Create: `scrapening-ofertas/.env.example`

- [ ] **Step 1: Instalar Apify CLI globalmente**

```bash
npm install -g apify-cli
apify --version
```
Esperado: versión impresa (ej. `1.x.x`)

- [ ] **Step 2: Iniciar el actor desde template**

```bash
cd "C:\Users\josea\Desktop\proyectos\paginas web\distribuidoras-con-descuentos"
apify create scrapening-ofertas
```

Selecciona template: **"Playwright + Chrome"** cuando lo pida el CLI.

- [ ] **Step 3: Reemplazar `scrapening-ofertas/package.json` con:**

```json
{
  "name": "scrapening-ofertas",
  "version": "1.0.0",
  "description": "Scraper de datazos de distribuidoras RM Chile",
  "type": "module",
  "main": "src/main.js",
  "scripts": {
    "start": "node src/main.js",
    "test": "jest --experimental-vm-modules",
    "dev": "apify run"
  },
  "dependencies": {
    "apify": "^3.0.0",
    "crawlee": "^3.0.0",
    "playwright": "^1.40.0",
    "googleapis": "^140.0.0"
  },
  "devDependencies": {
    "jest": "^29.0.0",
    "dotenv": "^16.0.0"
  }
}
```

- [ ] **Step 4: Crear `.actor/actor.json`**

```json
{
  "actorSpecification": 1,
  "name": "scrapening-ofertas",
  "title": "Scrapening Ofertas RM Chile",
  "description": "Monitorea TikTok, Instagram, YouTube y Facebook buscando datazos de distribuidoras y supermercados en la RM de Chile",
  "version": "1.0",
  "buildTag": "latest",
  "environmentVariables": [
    { "name": "YOUTUBE_API_KEY", "isSecret": true }
  ],
  "dockerfile": "./Dockerfile"
}
```

- [ ] **Step 5: Crear `.actor/input_schema.json`**

```json
{
  "title": "scrapening-ofertas Input",
  "type": "object",
  "schemaVersion": 1,
  "properties": {
    "cuentas": {
      "title": "Cuentas conocidas por plataforma",
      "type": "object",
      "description": "Handles a monitorear por plataforma",
      "editor": "json",
      "default": {
        "tiktok": ["matsi_matsi"],
        "instagram": ["matsi_matsi"],
        "youtube": [],
        "facebook": []
      }
    },
    "maxResultsPerSource": {
      "title": "Máximo de resultados por fuente",
      "type": "integer",
      "default": 20,
      "minimum": 1,
      "maximum": 100
    },
    "youtubeApiKey": {
      "title": "YouTube Data API v3 Key",
      "type": "string",
      "isSecret": true
    }
  },
  "required": []
}
```

- [ ] **Step 6: Crear `.env.example`**

```
YOUTUBE_API_KEY=tu_api_key_aqui
APIFY_TOKEN=tu_token_aqui
```

- [ ] **Step 7: Instalar dependencias**

```bash
cd scrapening-ofertas
npm install
```

Esperado: `node_modules/` creado sin errores.

- [ ] **Step 8: Commit**

```bash
git init
git add scrapening-ofertas/
git commit -m "feat: setup inicial del actor scrapening-ofertas"
```

---

## Task 2: Configuración y constantes

**Files:**
- Create: `scrapening-ofertas/src/config.js`
- Create: `scrapening-ofertas/tests/config.test.js`

- [ ] **Step 1: Escribir el test**

```javascript
// tests/config.test.js
import { DEFAULT_HASHTAGS, PLATFORMS, MAX_IDS_PER_PLATFORM } from '../src/config.js';

test('DEFAULT_HASHTAGS tiene entradas para todas las plataformas', () => {
    expect(DEFAULT_HASHTAGS.tiktok.length).toBeGreaterThan(0);
    expect(DEFAULT_HASHTAGS.instagram.length).toBeGreaterThan(0);
    expect(DEFAULT_HASHTAGS.youtube.length).toBeGreaterThan(0);
    expect(DEFAULT_HASHTAGS.facebook.length).toBeGreaterThan(0);
});

test('PLATFORMS contiene las 4 plataformas', () => {
    expect(PLATFORMS).toEqual(['tiktok', 'instagram', 'youtube', 'facebook']);
});

test('MAX_IDS_PER_PLATFORM es número positivo', () => {
    expect(MAX_IDS_PER_PLATFORM).toBeGreaterThan(0);
});
```

- [ ] **Step 2: Ejecutar test para verificar que falla**

```bash
cd scrapening-ofertas
npm test -- tests/config.test.js
```
Esperado: FAIL — "Cannot find module '../src/config.js'"

- [ ] **Step 3: Crear `src/config.js`**

```javascript
// src/config.js
export const PLATFORMS = ['tiktok', 'instagram', 'youtube', 'facebook'];

export const MAX_IDS_PER_PLATFORM = 10000;

export const DEFAULT_HASHTAGS = {
    tiktok: [
        'datazo', 'datazochile', 'distribuidora', 'distribuidorachile',
        'ofertachile', 'descuentochile', 'santiagochile', 'rmchile',
        'maipuchile', 'pudahuelchile', 'ofertasrm'
    ],
    instagram: [
        'datazo', 'datazochile', 'distribuidora',
        'ofertachile', 'descuentochile', 'ofertasrm'
    ],
    youtube: [
        'datazo distribuidora Region Metropolitana',
        'oferta distribuidora Santiago Chile',
        'descuento supermercado Chile'
    ],
    facebook: [
        'datazo', 'distribuidora RM', 'oferta Santiago'
    ]
};

export const SUPERMARKETS_ACCOUNTS = {
    tiktok: ['lider_chile', 'jumbo_cl', 'santaisabelchile', 'unimarc_cl'],
    instagram: ['liderchile', 'jumbochile', 'santaisabelchile', 'unimarc'],
    youtube: ['Lider Chile', 'Jumbo Chile', 'Santa Isabel Chile'],
    facebook: ['LiderChile', 'JumboChile', 'SantaIsabelChile']
};
```

- [ ] **Step 4: Ejecutar test para verificar que pasa**

```bash
npm test -- tests/config.test.js
```
Esperado: PASS

- [ ] **Step 5: Commit**

```bash
git add src/config.js tests/config.test.js
git commit -m "feat: configuración y constantes de scrapening-ofertas"
```

---

## Task 3: Módulo de deduplicación

**Files:**
- Create: `scrapening-ofertas/src/dedup.js`
- Create: `scrapening-ofertas/tests/dedup.test.js`

- [ ] **Step 1: Escribir el test**

```javascript
// tests/dedup.test.js
import { isNew, markProcessed, trimIds } from '../src/dedup.js';

test('isNew retorna true si el id no existe en la plataforma', () => {
    const ids = { tiktok: ['111', '222'] };
    expect(isNew(ids, 'tiktok', '333')).toBe(true);
});

test('isNew retorna false si el id ya existe', () => {
    const ids = { tiktok: ['111', '222'] };
    expect(isNew(ids, 'tiktok', '111')).toBe(false);
});

test('isNew retorna true para plataforma sin entradas previas', () => {
    const ids = {};
    expect(isNew(ids, 'instagram', 'abc123')).toBe(true);
});

test('markProcessed agrega el id a la plataforma correcta', () => {
    const ids = {};
    const result = markProcessed(ids, 'tiktok', '999');
    expect(result.tiktok).toContain('999');
});

test('markProcessed no modifica otras plataformas', () => {
    const ids = { instagram: ['abc'] };
    const result = markProcessed(ids, 'tiktok', '999');
    expect(result.instagram).toEqual(['abc']);
});

test('trimIds recorta al máximo cuando supera el límite', () => {
    const ids = Array.from({ length: 150 }, (_, i) => String(i));
    const trimmed = trimIds(ids, 100);
    expect(trimmed.length).toBe(100);
    expect(trimmed[0]).toBe('50'); // mantiene los últimos 100
});

test('trimIds no modifica si está bajo el límite', () => {
    const ids = ['a', 'b', 'c'];
    expect(trimIds(ids, 100)).toEqual(['a', 'b', 'c']);
});
```

- [ ] **Step 2: Ejecutar test para verificar que falla**

```bash
npm test -- tests/dedup.test.js
```
Esperado: FAIL — "Cannot find module '../src/dedup.js'"

- [ ] **Step 3: Crear `src/dedup.js`**

```javascript
// src/dedup.js
import { Actor } from 'apify';
import { MAX_IDS_PER_PLATFORM } from './config.js';

const STORE_KEY = 'processed_ids';

export function isNew(processedIds, platform, id) {
    return !processedIds[platform]?.includes(id);
}

export function markProcessed(processedIds, platform, id) {
    const updated = { ...processedIds };
    if (!updated[platform]) updated[platform] = [];
    updated[platform] = [...updated[platform], id];
    return updated;
}

export function trimIds(ids, max) {
    if (ids.length <= max) return ids;
    return ids.slice(ids.length - max);
}

export async function loadProcessedIds() {
    const store = await Actor.openKeyValueStore();
    return (await store.getValue(STORE_KEY)) || {};
}

export async function saveProcessedIds(ids) {
    const store = await Actor.openKeyValueStore();
    const trimmed = {};
    for (const [platform, platformIds] of Object.entries(ids)) {
        trimmed[platform] = trimIds(platformIds, MAX_IDS_PER_PLATFORM);
    }
    await store.setValue(STORE_KEY, trimmed);
}
```

- [ ] **Step 4: Ejecutar test para verificar que pasa**

```bash
npm test -- tests/dedup.test.js
```
Esperado: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add src/dedup.js tests/dedup.test.js
git commit -m "feat: módulo de deduplicación con KV Store"
```

---

## Task 4: Utilidades de browser (Playwright)

**Files:**
- Create: `scrapening-ofertas/src/browser.js`

- [ ] **Step 1: Crear `src/browser.js`**

```javascript
// src/browser.js
import { PlaywrightCrawler, ProxyConfiguration } from 'crawlee';
import { Actor } from 'apify';

export async function createBrowser() {
    const proxyConfiguration = await Actor.createProxyConfiguration({
        groups: ['RESIDENTIAL'],
    });

    return { proxyConfiguration };
}

export async function fetchPageWithRetry(url, extractFn, options = {}) {
    const { proxyConfiguration } = await createBrowser();
    let result = null;
    let error = null;

    const crawler = new PlaywrightCrawler({
        proxyConfiguration,
        maxRequestRetries: 3,
        requestHandlerTimeoutSecs: 60,
        headless: true,
        launchContext: {
            launchOptions: {
                args: ['--no-sandbox', '--disable-setuid-sandbox'],
            },
        },
        async requestHandler({ page, request }) {
            await page.waitForLoadState('networkidle', { timeout: 30000 });
            result = await extractFn(page, request.url);
        },
        async failedRequestHandler({ request }, err) {
            error = err;
        },
        ...options,
    });

    await crawler.run([url]);

    if (error && !result) throw error;
    return result || [];
}
```

- [ ] **Step 2: Commit**

```bash
git add src/browser.js
git commit -m "feat: utilidades de browser con Playwright y proxies"
```

---

## Task 5: Scraper de YouTube (API oficial)

**Files:**
- Create: `scrapening-ofertas/src/scrapers/youtube.js`
- Create: `scrapening-ofertas/tests/scrapers/youtube.test.js`

- [ ] **Step 1: Escribir el test**

```javascript
// tests/scrapers/youtube.test.js
import { buildVideoOutput, filterByDate } from '../../src/scrapers/youtube.js';

test('buildVideoOutput convierte item de YouTube API al formato estándar', () => {
    const item = {
        id: { videoId: 'abc123' },
        snippet: {
            title: 'Datazo mantequilla distribuidora',
            description: 'Gran oferta en Maipú',
            channelTitle: 'MatsiMatsi',
            publishedAt: '2026-06-24T10:00:00Z',
            thumbnails: { high: { url: 'https://img.youtube.com/abc123/hqdefault.jpg' } }
        }
    };

    const output = buildVideoOutput(item);

    expect(output.id).toBe('abc123');
    expect(output.url).toBe('https://www.youtube.com/watch?v=abc123');
    expect(output.plataforma).toBe('youtube');
    expect(output.cuenta).toBe('MatsiMatsi');
    expect(output.descripcion).toBe('Datazo mantequilla distribuidora — Gran oferta en Maipú');
    expect(output.miniatura_url).toBe('https://img.youtube.com/abc123/hqdefault.jpg');
    expect(output.fecha).toBe('2026-06-24');
    expect(output.video_url).toBe('https://www.youtube.com/watch?v=abc123');
});

test('filterByDate filtra videos anteriores al lastRunDate', () => {
    const items = [
        { snippet: { publishedAt: '2026-06-24T10:00:00Z' } },
        { snippet: { publishedAt: '2026-06-22T10:00:00Z' } },
        { snippet: { publishedAt: '2026-06-23T10:00:00Z' } },
    ];
    const filtered = filterByDate(items, '2026-06-23T00:00:00Z');
    expect(filtered.length).toBe(2); // solo 24 y 23
});
```

- [ ] **Step 2: Ejecutar test para verificar que falla**

```bash
npm test -- tests/scrapers/youtube.test.js
```
Esperado: FAIL

- [ ] **Step 3: Crear `src/scrapers/youtube.js`**

```javascript
// src/scrapers/youtube.js
import { google } from 'googleapis';

const youtube = google.youtube('v3');

export function buildVideoOutput(item) {
    const videoId = item.id.videoId;
    const url = `https://www.youtube.com/watch?v=${videoId}`;
    return {
        id: videoId,
        url,
        plataforma: 'youtube',
        cuenta: item.snippet.channelTitle,
        descripcion: `${item.snippet.title} — ${item.snippet.description}`.slice(0, 500),
        fecha: item.snippet.publishedAt.slice(0, 10),
        miniatura_url: item.snippet.thumbnails?.high?.url || item.snippet.thumbnails?.default?.url || '',
        video_url: url,
    };
}

export function filterByDate(items, lastRunDate) {
    if (!lastRunDate) return items;
    const since = new Date(lastRunDate);
    return items.filter(item => new Date(item.snippet.publishedAt) >= since);
}

export async function scrapeYoutubeByKeyword(apiKey, keyword, maxResults, lastRunDate) {
    const response = await youtube.search.list({
        auth: apiKey,
        part: 'snippet',
        q: keyword,
        type: 'video',
        maxResults: maxResults || 20,
        order: 'date',
        relevanceLanguage: 'es',
        regionCode: 'CL',
        publishedAfter: lastRunDate || undefined,
    });

    const items = response.data.items || [];
    return items.map(buildVideoOutput);
}

export async function scrapeYoutubeByChannel(apiKey, channelName, maxResults, lastRunDate) {
    // Buscar el channel ID por nombre
    const searchResponse = await youtube.search.list({
        auth: apiKey,
        part: 'snippet',
        q: channelName,
        type: 'channel',
        maxResults: 1,
    });

    if (!searchResponse.data.items?.length) return [];
    const channelId = searchResponse.data.items[0].id.channelId;

    const videosResponse = await youtube.search.list({
        auth: apiKey,
        part: 'snippet',
        channelId,
        type: 'video',
        maxResults: maxResults || 20,
        order: 'date',
        publishedAfter: lastRunDate || undefined,
    });

    const items = videosResponse.data.items || [];
    return items.map(buildVideoOutput);
}
```

- [ ] **Step 4: Ejecutar test para verificar que pasa**

```bash
npm test -- tests/scrapers/youtube.test.js
```
Esperado: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/scrapers/youtube.js tests/scrapers/youtube.test.js
git commit -m "feat: scraper YouTube con API Data v3"
```

---

## Task 6: Scraper de TikTok (Playwright)

**Files:**
- Create: `scrapening-ofertas/src/scrapers/tiktok.js`

- [ ] **Step 1: Crear `src/scrapers/tiktok.js`**

```javascript
// src/scrapers/tiktok.js
import { fetchPageWithRetry } from '../browser.js';

export function buildTikTokOutput(data) {
    return {
        id: data.id,
        url: `https://www.tiktok.com/@${data.author}/video/${data.id}`,
        plataforma: 'tiktok',
        cuenta: `@${data.author}`,
        descripcion: (data.desc || '').slice(0, 500),
        fecha: new Date(data.createTime * 1000).toISOString().slice(0, 10),
        miniatura_url: data.video?.cover || '',
        video_url: data.video?.playAddr || '',
    };
}

async function extractTikTokVideos(page, url) {
    // Espera que cargue el feed
    await page.waitForSelector('[data-e2e="user-post-item"], [data-e2e="challenge-item"]', {
        timeout: 15000,
    }).catch(() => null);

    // Extrae datos desde el __NEXT_DATA__ que TikTok inyecta en el HTML
    const data = await page.evaluate(() => {
        const el = document.getElementById('__NEXT_DATA__');
        if (!el) return null;
        try {
            const json = JSON.parse(el.textContent);
            // Navegar la estructura según el tipo de página
            const props = json?.props?.pageProps;
            return props?.items || props?.itemList || [];
        } catch {
            return null;
        }
    });

    return data || [];
}

export async function scrapeTikTokAccount(handle, maxResults) {
    const url = `https://www.tiktok.com/@${handle}`;
    const items = await fetchPageWithRetry(url, extractTikTokVideos);
    return items.slice(0, maxResults).map(item => buildTikTokOutput({
        id: item.id,
        author: handle,
        desc: item.desc,
        createTime: item.createTime,
        video: item.video,
    }));
}

export async function scrapeTikTokHashtag(hashtag, maxResults) {
    const url = `https://www.tiktok.com/tag/${encodeURIComponent(hashtag)}`;
    const items = await fetchPageWithRetry(url, extractTikTokVideos);
    return items.slice(0, maxResults).map(item => buildTikTokOutput({
        id: item.id,
        author: item.author?.uniqueId || 'unknown',
        desc: item.desc,
        createTime: item.createTime,
        video: item.video,
    }));
}
```

- [ ] **Step 2: Commit**

```bash
git add src/scrapers/tiktok.js
git commit -m "feat: scraper TikTok con Playwright"
```

---

## Task 7: Scraper de Instagram (Playwright)

**Files:**
- Create: `scrapening-ofertas/src/scrapers/instagram.js`

- [ ] **Step 1: Crear `src/scrapers/instagram.js`**

```javascript
// src/scrapers/instagram.js
import { fetchPageWithRetry } from '../browser.js';

export function buildInstagramOutput(data) {
    const shortcode = data.shortcode || data.code;
    return {
        id: data.id,
        url: `https://www.instagram.com/p/${shortcode}/`,
        plataforma: 'instagram',
        cuenta: `@${data.owner?.username || data.user?.username || 'unknown'}`,
        descripcion: (data.edge_media_to_caption?.edges?.[0]?.node?.text || data.caption?.text || '').slice(0, 500),
        fecha: new Date((data.taken_at_timestamp || data.taken_at) * 1000).toISOString().slice(0, 10),
        miniatura_url: data.thumbnail_src || data.image_versions2?.candidates?.[0]?.url || '',
        video_url: data.video_url || data.video_versions?.[0]?.url || '',
    };
}

async function extractInstagramPosts(page) {
    await page.waitForTimeout(3000);

    const data = await page.evaluate(() => {
        // Instagram inyecta datos en scripts con type="application/ld+json" y en window.__additionalData
        try {
            const scripts = Array.from(document.querySelectorAll('script[type="application/json"]'));
            for (const script of scripts) {
                const json = JSON.parse(script.textContent);
                const items = json?.require?.[0]?.[3]?.[0]?.__bbox?.result?.data?.user?.edge_owner_to_timeline_media?.edges
                    || json?.data?.recent?.sections?.flatMap(s => s.layout_content?.medias?.map(m => m.media)) || [];
                if (items.length > 0) return items.map(e => e.node || e);
            }
        } catch {}
        return [];
    });

    return data || [];
}

export async function scrapeInstagramAccount(handle, maxResults) {
    const url = `https://www.instagram.com/${handle}/reels/`;
    const items = await fetchPageWithRetry(url, extractInstagramPosts);
    return items.slice(0, maxResults).map(buildInstagramOutput);
}

export async function scrapeInstagramHashtag(hashtag, maxResults) {
    const url = `https://www.instagram.com/explore/tags/${encodeURIComponent(hashtag)}/`;
    const items = await fetchPageWithRetry(url, extractInstagramPosts);
    return items.slice(0, maxResults).map(buildInstagramOutput);
}
```

- [ ] **Step 2: Commit**

```bash
git add src/scrapers/instagram.js
git commit -m "feat: scraper Instagram con Playwright"
```

---

## Task 8: Scraper de Facebook (Playwright)

**Files:**
- Create: `scrapening-ofertas/src/scrapers/facebook.js`

- [ ] **Step 1: Crear `src/scrapers/facebook.js`**

```javascript
// src/scrapers/facebook.js
import { fetchPageWithRetry } from '../browser.js';

export function buildFacebookOutput(data) {
    return {
        id: data.id,
        url: data.url || `https://www.facebook.com/reel/${data.id}`,
        plataforma: 'facebook',
        cuenta: data.owner?.name || data.pageName || 'unknown',
        descripcion: (data.message?.text || data.description || '').slice(0, 500),
        fecha: data.creation_time
            ? new Date(data.creation_time * 1000).toISOString().slice(0, 10)
            : new Date().toISOString().slice(0, 10),
        miniatura_url: data.thumbnailImage?.uri || '',
        video_url: data.playable_url || data.source || '',
    };
}

async function extractFacebookReels(page) {
    await page.waitForTimeout(4000);

    const data = await page.evaluate(() => {
        try {
            const scripts = Array.from(document.querySelectorAll('script[type="application/json"]'));
            for (const script of scripts) {
                const json = JSON.parse(script.textContent);
                // Facebook usa Relay: busca arrays de nodos de video
                const str = JSON.stringify(json);
                if (str.includes('playable_url')) {
                    const matches = str.match(/"id":"(\d+)"[^}]*"playable_url":"([^"]+)"/g);
                    if (matches?.length) return [{ id: 'found', raw: matches }];
                }
            }
        } catch {}
        return [];
    });

    return data || [];
}

export async function scrapeFacebookPage(pageName, maxResults) {
    const url = `https://www.facebook.com/${pageName}/reels/`;
    const items = await fetchPageWithRetry(url, extractFacebookReels);
    return items.slice(0, maxResults).map(buildFacebookOutput);
}

export async function scrapeFacebookKeyword(keyword, maxResults) {
    // Facebook no tiene búsqueda pública por hashtag fácilmente accesible.
    // Busca en páginas conocidas de supermercados/distribuidoras.
    // Esta función se expande en versiones futuras con más fuentes conocidas.
    const url = `https://www.facebook.com/search/videos/?q=${encodeURIComponent(keyword + ' Chile')}`;
    const items = await fetchPageWithRetry(url, extractFacebookReels);
    return items.slice(0, maxResults).map(buildFacebookOutput);
}
```

- [ ] **Step 2: Commit**

```bash
git add src/scrapers/facebook.js
git commit -m "feat: scraper Facebook con Playwright"
```

---

## Task 9: Orquestador principal (main.js)

**Files:**
- Create: `scrapening-ofertas/src/main.js`

- [ ] **Step 1: Crear `src/main.js`**

```javascript
// src/main.js
import { Actor, Dataset } from 'apify';
import { DEFAULT_HASHTAGS, SUPERMARKETS_ACCOUNTS, PLATFORMS } from './config.js';
import { loadProcessedIds, saveProcessedIds, isNew, markProcessed } from './dedup.js';
import { scrapeYoutubeByKeyword, scrapeYoutubeByChannel } from './scrapers/youtube.js';
import { scrapeTikTokAccount, scrapeTikTokHashtag } from './scrapers/tiktok.js';
import { scrapeInstagramAccount, scrapeInstagramHashtag } from './scrapers/instagram.js';
import { scrapeFacebookPage, scrapeFacebookKeyword } from './scrapers/facebook.js';

await Actor.init();

const input = await Actor.getInput() || {};
const {
    cuentas = {},
    maxResultsPerSource = 20,
    youtubeApiKey = process.env.YOUTUBE_API_KEY,
} = input;

// Merge cuentas del input con cuentas de supermercados
const allCuentas = {};
for (const platform of PLATFORMS) {
    allCuentas[platform] = [
        ...(cuentas[platform] || []),
        ...(SUPERMARKETS_ACCOUNTS[platform] || []),
    ];
}

let processedIds = await loadProcessedIds();
let newItemsCount = 0;

async function pushIfNew(item) {
    if (!item.id) return;
    if (!isNew(processedIds, item.plataforma, item.id)) return;
    await Dataset.pushData(item);
    processedIds = markProcessed(processedIds, item.plataforma, item.id);
    newItemsCount++;
}

// ── TikTok ──────────────────────────────────────────
console.log('Scraping TikTok cuentas...');
for (const handle of allCuentas.tiktok || []) {
    try {
        const items = await scrapeTikTokAccount(handle, maxResultsPerSource);
        for (const item of items) await pushIfNew(item);
    } catch (e) {
        console.error(`TikTok cuenta @${handle} error:`, e.message);
    }
}

console.log('Scraping TikTok hashtags...');
for (const hashtag of DEFAULT_HASHTAGS.tiktok) {
    try {
        const items = await scrapeTikTokHashtag(hashtag, maxResultsPerSource);
        for (const item of items) await pushIfNew(item);
    } catch (e) {
        console.error(`TikTok hashtag #${hashtag} error:`, e.message);
    }
}

// ── Instagram ────────────────────────────────────────
console.log('Scraping Instagram cuentas...');
for (const handle of allCuentas.instagram || []) {
    try {
        const items = await scrapeInstagramAccount(handle, maxResultsPerSource);
        for (const item of items) await pushIfNew(item);
    } catch (e) {
        console.error(`Instagram cuenta @${handle} error:`, e.message);
    }
}

console.log('Scraping Instagram hashtags...');
for (const hashtag of DEFAULT_HASHTAGS.instagram) {
    try {
        const items = await scrapeInstagramHashtag(hashtag, maxResultsPerSource);
        for (const item of items) await pushIfNew(item);
    } catch (e) {
        console.error(`Instagram hashtag #${hashtag} error:`, e.message);
    }
}

// ── YouTube ──────────────────────────────────────────
if (youtubeApiKey) {
    console.log('Scraping YouTube keywords...');
    for (const keyword of DEFAULT_HASHTAGS.youtube) {
        try {
            const items = await scrapeYoutubeByKeyword(youtubeApiKey, keyword, maxResultsPerSource);
            for (const item of items) await pushIfNew(item);
        } catch (e) {
            console.error(`YouTube keyword "${keyword}" error:`, e.message);
        }
    }

    console.log('Scraping YouTube canales...');
    for (const channel of allCuentas.youtube || []) {
        try {
            const items = await scrapeYoutubeByChannel(youtubeApiKey, channel, maxResultsPerSource);
            for (const item of items) await pushIfNew(item);
        } catch (e) {
            console.error(`YouTube canal "${channel}" error:`, e.message);
        }
    }
} else {
    console.warn('YOUTUBE_API_KEY no configurada — saltando YouTube');
}

// ── Facebook ─────────────────────────────────────────
console.log('Scraping Facebook páginas...');
for (const page of allCuentas.facebook || []) {
    try {
        const items = await scrapeFacebookPage(page, maxResultsPerSource);
        for (const item of items) await pushIfNew(item);
    } catch (e) {
        console.error(`Facebook página ${page} error:`, e.message);
    }
}

console.log('Scraping Facebook keywords...');
for (const keyword of DEFAULT_HASHTAGS.facebook) {
    try {
        const items = await scrapeFacebookKeyword(keyword, maxResultsPerSource);
        for (const item of items) await pushIfNew(item);
    } catch (e) {
        console.error(`Facebook keyword "${keyword}" error:`, e.message);
    }
}

// ── Guardar IDs procesados ───────────────────────────
await saveProcessedIds(processedIds);
console.log(`✅ scrapening-ofertas completado. ${newItemsCount} nuevos items encontrados.`);

await Actor.exit();
```

- [ ] **Step 2: Commit**

```bash
git add src/main.js
git commit -m "feat: orquestador principal de scrapening-ofertas"
```

---

## Task 10: Deploy a Apify Cloud + configurar scheduler

**Files:**
- Modify: `scrapening-ofertas/.actor/actor.json` (agregar build config)

- [ ] **Step 1: Login en Apify CLI**

```bash
apify login
```
Ingresa tu Apify API token cuando lo pida. Lo encuentras en https://console.apify.com/account/integrations

- [ ] **Step 2: Deploy el actor**

```bash
cd scrapening-ofertas
apify push
```
Esperado: actor subido y visible en https://console.apify.com/actors

- [ ] **Step 3: Configurar variable de entorno YOUTUBE_API_KEY**

En https://console.apify.com → tu actor → Settings → Environment Variables:
- Name: `YOUTUBE_API_KEY`
- Value: tu API key de YouTube Data v3
- Secret: ✅

Para obtener una YouTube API key:
1. https://console.cloud.google.com → nuevo proyecto → "YouTube Data API v3" → Enable → Credentials → Create API Key

- [ ] **Step 4: Configurar el scheduler**

En Apify Console → tu actor → Schedules → New Schedule:
- Cron expression: `0 8,13,19 * * *` (ejecuta a las 8:00, 13:00 y 19:00)
- Input: `{ "maxResultsPerSource": 20 }`
- Timezone: America/Santiago

- [ ] **Step 5: Hacer un test run manual**

En Apify Console → tu actor → Run → Start:
- Input: `{ "maxResultsPerSource": 5 }` (poco para probar rápido)
- Verificar que el dataset tenga resultados con la estructura:
  ```json
  {
    "id": "...",
    "url": "...",
    "plataforma": "youtube",
    "cuenta": "...",
    "descripcion": "...",
    "fecha": "2026-06-24",
    "miniatura_url": "...",
    "video_url": "..."
  }
  ```

- [ ] **Step 6: Commit final**

```bash
cd ..
git add scrapening-ofertas/
git commit -m "feat: scrapening-ofertas completo y deployado en Apify"
```

---

## Output del Actor

Cada item en el Dataset tiene este formato estándar (consumido por el Pipeline IA en Plan 2):

```json
{
  "id": "7380000000000000000",
  "url": "https://www.tiktok.com/@matsi_matsi/video/7380000000000000000",
  "plataforma": "tiktok",
  "cuenta": "@matsi_matsi",
  "descripcion": "Datazo de mantequilla sin lactosa Quillayes a $1.000 💥",
  "fecha": "2026-06-24",
  "miniatura_url": "https://p16-sign.tiktokcdn.com/...",
  "video_url": "https://v19.tiktok.com/..."
}
```

---

## Próximos planes

- **Plan 2:** Pipeline IA — filtro con Claude Vision + Whisper, enriquecimiento web, generación de imágenes con Pillow y FFmpeg
- **Plan 3:** Publicador + Sitio Web — Meta API, TikTok API, WhatsApp Business, Telegram Bot, Next.js
