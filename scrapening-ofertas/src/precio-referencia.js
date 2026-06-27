import { chromium } from 'playwright-extra';
import stealthPlugin from 'puppeteer-extra-plugin-stealth';
import { pathToFileURL } from 'node:url';

// Stealth global: evade detección de anti-bots (PerimeterX en Líder, etc.).
// No afecta a los supermercados sin protección.
chromium.use(stealthPlugin());

// ─────────────────────────────────────────────────────────────────────────────
// Extractor de PRECIO DE REFERENCIA de supermercados (Jumbo, Santa Isabel).
// Dado el nombre de un producto, busca cuánto cuesta en el supermercado para
// enriquecer un datazo y calcular el % de ahorro real.
//
// ¿Por qué navegador y no fetch directo?
//   No existe API pública. Los sitios sirven el shell SPA a curl y bloquean
//   bots con anti-bot (Akamai → 403). Abrir la página de búsqueda en un
//   navegador real dispara el XHR legítimo de productos y lo interceptamos:
//   es la vía robusta y la única que pasa el anti-bot.
//
// Hallazgo (jun 2026): Cencosud (Jumbo + Santa Isabel) MIGRÓ DE VTEX a un BFF
//   propio →  https://bff.<tienda>.cl/catalog/plp  (respuesta JSON rica, con
//   precio, precio/unidad y promociones). Unimarc es Next.js + Akamai (ver
//   SUPERMERCADOS.unimarc, aún no soportado).
// ─────────────────────────────────────────────────────────────────────────────

const USER_AGENT =
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
    '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';

// ─── Normalización: Cencosud BFF (Jumbo / Santa Isabel) ──────────────────────
// Shape real:  { products: [ { brand, slug, items: [ { name, price, listPrice,
//   ppumPrice, measurementUnitUn, stock, images[], promotions[] } ] } ] }

function normalizarProductoCencosud(p) {
    const it = p?.items?.[0];
    if (!it || it.price == null) return null;

    const promoCruda = Array.isArray(it.promotions) && it.promotions.length ? it.promotions[0] : null;
    const promo = promoCruda
        ? {
              descripcion: promoCruda.name || '',
              tipo: promoCruda.type || '',
              precio: promoCruda.value ?? null, // precio total de la promo (ej. 2x$2990 → 2990)
              precioUnitario: promoCruda.unitPrice ?? null, // precio por unidad bajo la promo
              cantidad: promoCruda.mQuantity ?? null, // unidades requeridas (ej. 2)
          }
        : null;

    const precioLista = it.listPrice ?? it.price;
    return {
        nombre: it.name || p.slug || '',
        marca: p.brand || '',
        precio: it.price,
        precioLista,
        ahorroPct: precioLista > it.price ? Math.round(((precioLista - it.price) / precioLista) * 100) : 0,
        disponible: !!it.stock,
        precioPorUnidad: it.ppumPrice ?? null, // ej. $/lt o $/kg — ideal para comparar
        unidadMedida: it.measurementUnitUn || it.measurementUnit || '',
        promo,
        imagen: it.images?.[0] || '',
        sku: String(it.skuId ?? p.productId ?? ''),
        slug: p.slug || '',
    };
}

export function normalizarProductosCencosud(json) {
    const lista = Array.isArray(json?.products) ? json.products : [];
    return lista.map(normalizarProductoCencosud).filter(Boolean);
}

// ─── Normalización: VTEX genérico (helper para otras tiendas VTEX) ────────────
// VTEX devuelve productos como array plano, { products } o GraphQL
// { data.productSearch.products }. Se conserva por si se agrega una tienda VTEX.

export function extraerListaProductosVtex(json) {
    if (Array.isArray(json)) return json;
    if (!json || typeof json !== 'object') return [];
    if (Array.isArray(json.products)) return json.products;
    const ps = json?.data?.productSearch?.products;
    if (Array.isArray(ps)) return ps;
    return [];
}

function ofertaVtex(producto) {
    const item = producto?.items?.[0];
    const seller =
        item?.sellers?.find((s) => s?.commertialOffer?.AvailableQuantity > 0) || item?.sellers?.[0];
    return seller?.commertialOffer || null;
}

export function normalizarProductoVtex(producto) {
    const oferta = ofertaVtex(producto);
    if (!oferta) return null;
    const precio = oferta.Price ?? oferta.spotPrice ?? null;
    if (precio == null) return null;
    const precioLista = oferta.ListPrice ?? precio;
    return {
        nombre: producto.productName || producto.productTitle || '',
        marca: producto.brand || '',
        precio,
        precioLista,
        ahorroPct: precioLista > precio ? Math.round(((precioLista - precio) / precioLista) * 100) : 0,
        disponible: (oferta.AvailableQuantity ?? 0) > 0,
        precioPorUnidad: null,
        unidadMedida: '',
        promo: null,
        imagen: producto.items?.[0]?.images?.[0]?.imageUrl || '',
        sku: String(producto.productId ?? ''),
        slug: producto.linkText || '',
    };
}

export function normalizarProductosVtex(json) {
    return extraerListaProductosVtex(json).map(normalizarProductoVtex).filter(Boolean);
}

// ─── Normalización: Tottus (Falabella, Next.js SSR) ──────────────────────────
// Los productos NO vienen por XHR: están embebidos en el HTML, en
// __NEXT_DATA__ → props.pageProps.results[]. Cada producto trae prices[] con
// tipos: internetPrice (precio a pagar, crossed:false) y normalPrice (precio
// lista, crossed:true). Precios en formato chileno: "20.990".

function parsePrecioCL(valor) {
    const s = Array.isArray(valor) ? valor[0] : valor;
    if (s == null) return null;
    const n = parseInt(String(s).replace(/[^\d]/g, ''), 10);
    return Number.isFinite(n) ? n : null;
}

function normalizarProductoTottus(p) {
    const precios = Array.isArray(p.prices) ? p.prices : [];
    const internet =
        precios.find((x) => x.type === 'internetPrice' && !x.crossed) || precios.find((x) => !x.crossed);
    const normal = precios.find((x) => x.crossed) || precios.find((x) => x.type === 'normalPrice');

    const base = internet || precios[0];
    const precio = parsePrecioCL(base?.price);
    if (precio == null) return null;
    const precioLista = parsePrecioCL(normal?.price) ?? precio;

    // El supermercado (tottus.cl) incluye pum = precio por unidad de medida.
    const pum = base?.pum;
    return {
        nombre: p.displayName || '',
        marca: p.brand || '',
        precio,
        precioLista,
        ahorroPct: precioLista > precio ? Math.round(((precioLista - precio) / precioLista) * 100) : 0,
        disponible: true, // el listing no expone stock fiable; si aparece, asumimos disponible
        precioPorUnidad: pum ? parsePrecioCL(pum.price) : null,
        unidadMedida: pum?.label || '',
        promo: null,
        imagen: p.mediaUrls?.[0] || p.media?.[0]?.url || '',
        sku: String(p.skuId ?? p.productId ?? ''),
        slug: '',
        url: p.url || '', // Tottus ya entrega la URL completa del producto
    };
}

export function normalizarProductosTottus(json) {
    const res = json?.props?.pageProps?.results;
    return Array.isArray(res) ? res.map(normalizarProductoTottus).filter(Boolean) : [];
}

// ─── Normalización: Unimarc (SMU, BFF propio) ────────────────────────────────
// API: https://bff-unimarc-ecommerce.unimarc.cl/catalog/product/search
// Shape: { availableProducts: [ { price, promotion, item } ], notAvailableProducts }
//   price.price / price.listPrice → strings "$1.690"
//   price.ppum → "$1.690 x litro"
//   promotion.descriptionMessage → "2 x $2.000"
//   item.{ nameComplete, brand, sku, slug }

function precioYUnidad(ppum) {
    // "$1.690 x litro" → { precio: 1690, unidad: 'litro' }
    const precio = parsePrecioCL(ppum);
    const m = /x\s*(.+)$/i.exec(ppum || '');
    return { precio, unidad: m ? m[1].trim() : '' };
}

function normalizarProductoUnimarc(entry, disponible) {
    const it = entry?.item;
    const pr = entry?.price;
    if (!it || !pr) return null;
    const precio = parsePrecioCL(pr.price);
    if (precio == null) return null;
    const precioLista = parsePrecioCL(pr.listPrice ?? pr.priceWithoutDiscount) ?? precio;
    const ppum = precioYUnidad(pr.ppum);

    const promoCruda = entry.promotion?.hasSavings ? entry.promotion : null;
    const promo = promoCruda
        ? {
              descripcion: promoCruda.descriptionMessage || promoCruda.name || '',
              tipo: promoCruda.type || '',
              precio: promoCruda.price ?? null,
              precioUnitario: promoCruda.price ?? null,
              cantidad: promoCruda.itemsRequiredForPromotion ?? null,
          }
        : null;

    return {
        nombre: it.nameComplete || it.name || '',
        marca: it.brand || '',
        precio,
        precioLista,
        ahorroPct: precioLista > precio ? Math.round(((precioLista - precio) / precioLista) * 100) : 0,
        disponible: !!disponible && (pr.availableQuantity ?? 1) > 0,
        precioPorUnidad: ppum.precio,
        unidadMedida: ppum.unidad,
        promo,
        imagen: it.images?.[0]?.url || it.image || '',
        sku: String(it.sku ?? it.itemId ?? ''),
        slug: it.slug || it.detailUrl || '',
    };
}

export function normalizarProductosUnimarc(json) {
    const disp = Array.isArray(json?.availableProducts)
        ? json.availableProducts.map((e) => normalizarProductoUnimarc(e, true))
        : [];
    const noDisp = Array.isArray(json?.notAvailableProducts)
        ? json.notAvailableProducts.map((e) => normalizarProductoUnimarc(e, false))
        : [];
    return [...disp, ...noDisp].filter(Boolean);
}

// ─── Normalización: Líder (Walmart Chile, GraphQL) ───────────────────────────
// API: https://super.lider.cl/orchestra/graphql/search?query=...  (tras pasar
// PerimeterX con stealth). Items en data.search.searchResult.itemStacks[].itemsV2
//   priceInfo.currentPrice.price (número) / .wasPrice / .listPrice
//   priceInfo.unitPrice.priceString → "$1.000 x lt"
//   availabilityStatusV2.value → "IN_STOCK"
//   canonicalUrl → "/ip/..."  (relativa)

function normalizarProductoLider(it) {
    const pi = it?.priceInfo;
    const precio = pi?.currentPrice?.price ?? parsePrecioCL(pi?.currentPrice?.priceString);
    if (precio == null) return null;
    const precioLista =
        pi?.wasPrice?.price ??
        pi?.listPrice?.price ??
        parsePrecioCL(pi?.wasPrice?.priceString) ??
        parsePrecioCL(pi?.listPrice?.priceString) ??
        precio;
    const u = precioYUnidad(pi?.unitPrice?.priceString);

    return {
        nombre: it.name || '',
        marca: it.brand || '',
        precio,
        precioLista,
        ahorroPct: precioLista > precio ? Math.round(((precioLista - precio) / precioLista) * 100) : 0,
        disponible: (it.availabilityStatusV2?.value || it.availabilityStatus || '') === 'IN_STOCK',
        precioPorUnidad: u.precio,
        unidadMedida: u.unidad,
        promo: null, // los descuentos de Líder vienen en wasPrice/savingsAmount → reflejados en ahorroPct
        imagen: it.imageInfo?.thumbnailUrl || '',
        sku: String(it.usItemId ?? it.id ?? ''),
        slug: '',
        url: it.canonicalUrl || '', // relativa; el fetcher la prefija con baseUrl
    };
}

export function normalizarProductosLider(json) {
    const stacks = json?.data?.search?.searchResult?.itemStacks;
    if (!Array.isArray(stacks)) return [];
    return stacks
        .flatMap((s) => (Array.isArray(s?.itemsV2) ? s.itemsV2 : []))
        .map(normalizarProductoLider)
        .filter(Boolean);
}

// ─── Supermercados soportados ────────────────────────────────────────────────

// metodo: 'xhr'      → intercepta el XHR de productos (matchApi)
//         'nextdata' → lee los productos embebidos en __NEXT_DATA__ (SSR)
export const SUPERMERCADOS = {
    jumbo: {
        nombre: 'Jumbo',
        soportado: true,
        metodo: 'xhr',
        baseUrl: 'https://www.jumbo.cl',
        searchUrl: (q) => `https://www.jumbo.cl/busqueda?ft=${encodeURIComponent(q)}`,
        matchApi: (url) => url.includes('/catalog/plp'),
        parse: normalizarProductosCencosud,
    },
    santaisabel: {
        nombre: 'Santa Isabel',
        soportado: true,
        metodo: 'xhr',
        baseUrl: 'https://www.santaisabel.cl',
        searchUrl: (q) => `https://www.santaisabel.cl/busqueda?ft=${encodeURIComponent(q)}`,
        matchApi: (url) => url.includes('/catalog/plp'),
        parse: normalizarProductosCencosud,
    },
    // Tottus (supermercado, www.tottus.cl — NO tottus.falabella.com, que es el
    // catálogo general de Falabella sin alimentos). Next.js SSR: los productos
    // vienen en __NEXT_DATA__ → props.pageProps.results. Tras Akamai: warmup en
    // la home + búsqueda por el buscador con stealth devuelve el SSR con datos.
    tottus: {
        nombre: 'Tottus',
        soportado: true,
        metodo: 'nextdata',
        usarBuscador: true,
        warmupUrl: 'https://www.tottus.cl/tottus-cl',
        warmupMs: 7000,
        baseUrl: 'https://www.tottus.cl',
        searchUrl: (q) => `https://www.tottus.cl/tottus-cl/buscar?Ntt=${encodeURIComponent(q).replace(/%20/g, '+')}`,
        parse: normalizarProductosTottus,
    },
    // Unimarc (SMU): Next.js, pero los productos cargan por XHR a su BFF propio.
    // Ruta de búsqueda: /search?q=<termino-con-guiones> (espacios → '-').
    // Conviene pasar antes por la home (warmup) para tomar cookies y evitar
    // fricción de Akamai.
    unimarc: {
        nombre: 'Unimarc',
        soportado: true,
        metodo: 'xhr',
        warmupUrl: 'https://www.unimarc.cl/',
        baseUrl: 'https://www.unimarc.cl',
        searchUrl: (q) =>
            `https://www.unimarc.cl/search?q=${encodeURIComponent(q.trim().toLowerCase().replace(/\s+/g, '-'))}`,
        matchApi: (url) => url.includes('catalog/product/search'),
        parse: normalizarProductosUnimarc,
    },
    // Líder (Walmart Chile): protegido con PerimeterX. Se pasa con stealth +
    // warmup en la home (que además fija la tienda por defecto). Ruta SPA:
    // /search?q=<termino+con+plus>. API de productos: /orchestra/graphql/search.
    // Líder (Walmart Chile): PerimeterX con captcha press-and-hold. El stealth
    // local lo pasa solo de forma intermitente → requiereAntiBot. Con un endpoint
    // Bright Data (BRD_BROWSER_WS) funciona de forma confiable. El parser y la
    // ruta están verificados contra datos reales.
    lider: {
        nombre: 'Líder',
        soportado: true,
        requiereAntiBot: true,
        metodo: 'xhr',
        usarBuscador: true, // el SPA dispara la búsqueda al tipear, no por URL
        warmupUrl: 'https://super.lider.cl/',
        warmupMs: 6000, // PerimeterX necesita tiempo para resolver su challenge JS
        baseUrl: 'https://super.lider.cl',
        searchUrl: (q) => `https://super.lider.cl/search?q=${encodeURIComponent(q).replace(/%20/g, '+')}`,
        matchApi: (url) => url.includes('/orchestra/graphql/search'),
        parse: normalizarProductosLider,
    },
};

// ─── Selección de mejor coincidencia ─────────────────────────────────────────

function puntajeCoincidencia(texto, query) {
    // Tokeniza en palabras completas (sin tildes ni puntuación). Compara por
    // palabra exacta para evitar falsos positivos por substring
    // (ej. "cola" NO debe matchear dentro de "colador").
    const palabras = (s) =>
        (s || '')
            .toLowerCase()
            .normalize('NFD')
            .replace(/[̀-ͯ]/g, '')
            .split(/[^a-z0-9]+/)
            .filter(Boolean);
    const setTexto = new Set(palabras(texto));
    const tokens = palabras(query);
    if (!tokens.length) return 0;
    return tokens.filter((tk) => setTexto.has(tk)).length / tokens.length;
}

// Elige el precio de referencia más representativo: prioriza coincidencia con la
// query y disponibilidad; entre iguales, el más barato.
export function mejorPrecio(productos, query) {
    const candidatos = productos
        .map((p) => ({ ...p, _match: puntajeCoincidencia(`${p.marca} ${p.nombre}`, query) }))
        .filter((p) => p._match >= 0.5);

    const lista = candidatos.length ? candidatos : productos.map((p) => ({ ...p, _match: 0 }));
    if (!lista.length) return null;

    lista.sort((a, b) => {
        if (a.disponible !== b.disponible) return a.disponible ? -1 : 1;
        if (b._match !== a._match) return b._match - a._match;
        return a.precio - b.precio;
    });

    const { _match, ...mejor } = lista[0];
    return mejor;
}

// ─── Fetcher con navegador ───────────────────────────────────────────────────

// Busca el precio de referencia de `query` en un supermercado.
// Devuelve { mercado, query, productos[], mejor }.  `mejor` es null si no hay.
export async function buscarPrecioReferencia(query, opciones = {}) {
    const { mercado = 'jumbo', headless = true, timeoutMs = 30000 } = opciones;
    const cfg = SUPERMERCADOS[mercado];
    if (!cfg) throw new Error(`Supermercado no soportado: ${mercado}`);
    if (!cfg.soportado) throw new Error(`${cfg.nombre} aún no está soportado (Next.js + Akamai)`);

    // Para sitios con anti-bot comercial (Líder→PerimeterX, Tottus→Akamai) el
    // stealth local pasa solo de forma intermitente. Si se define un endpoint de
    // Bright Data Scraping Browser (env BRD_BROWSER_WS o opción antiBotWs), nos
    // conectamos a ese navegador gestionado (proxies residenciales + solver),
    // que sí los resuelve de forma confiable.
    const wsEndpoint = opciones.antiBotWs || process.env.BRD_BROWSER_WS || null;
    const usarAntiBot = (cfg.requiereAntiBot || opciones.antiBot) && wsEndpoint;
    const browser = usarAntiBot
        ? await chromium.connectOverCDP(wsEndpoint)
        : await chromium.launch({ headless, args: ['--no-sandbox', '--disable-setuid-sandbox'] });
    try {
        const context = await browser.newContext({ userAgent: USER_AGENT, locale: 'es-CL' });
        const page = await context.newPage();

        // Warmup opcional: visitar la home primero para tomar cookies (anti-bot).
        if (cfg.warmupUrl) {
            await page.goto(cfg.warmupUrl, { waitUntil: 'domcontentloaded', timeout: timeoutMs }).catch(() => null);
            await page.waitForTimeout(cfg.warmupMs || 2000);

            // Si el sitio nos sirvió un muro anti-bot y NO estamos usando un
            // navegador gestionado, fallar con un mensaje accionable.
            if (cfg.requiereAntiBot && !usarAntiBot) {
                const t = (await page.title().catch(() => '')) || '';
                const u = page.url();
                if (/robot or human|un momento|just a moment|access denied/i.test(t) || /\/blocked/i.test(u)) {
                    throw new Error(
                        `${cfg.nombre}: bloqueado por anti-bot (${t || u}). Configura BRD_BROWSER_WS ` +
                            `(Bright Data Scraping Browser) para resolverlo de forma confiable.`,
                    );
                }
            }
        }

        // Navega a los resultados: tipeando en el buscador (cfg.usarBuscador) o
        // por URL directa. Algunos SPA solo disparan la búsqueda al tipear.
        const navegar = async () => {
            if (cfg.usarBuscador) {
                const selector =
                    cfg.inputSelector ||
                    'input[type="search"], input[placeholder*="usca" i], input[name*="search" i], input[id*="search" i]';
                const el = await page.waitForSelector(selector, { timeout: timeoutMs }).catch(() => null);
                if (!el) throw new Error(`${cfg.nombre}: no se encontró el buscador en la página`);
                await el.click().catch(() => null);
                await el.fill(query).catch(() => null);
                await page.keyboard.press('Enter').catch(() => null);
            } else {
                // 'networkidle' nunca se cumple (analytics de fondo) → solo DOM.
                await page.goto(cfg.searchUrl(query), { waitUntil: 'domcontentloaded', timeout: timeoutMs });
            }
        };

        let crudos = [];

        if (cfg.metodo === 'nextdata') {
            // Tottus: productos embebidos en __NEXT_DATA__ (SSR).
            await navegar();
            await page.waitForTimeout(3500); // dejar cargar el SSR de resultados
            const txt = await page.evaluate(() => {
                const el = document.getElementById('__NEXT_DATA__');
                return el ? el.textContent : null;
            });
            if (txt) {
                try {
                    crudos = cfg.parse(JSON.parse(txt));
                } catch {
                    /* __NEXT_DATA__ ilegible */
                }
            }
        } else {
            // Interceptamos el XHR de productos del supermercado.
            const capturas = [];
            const esApiProductos = (resp) =>
                cfg.matchApi(resp.url()) && (resp.headers()['content-type'] || '').includes('json');
            page.on('response', async (resp) => {
                try {
                    if (esApiProductos(resp)) capturas.push(await resp.json());
                } catch {
                    /* respuesta no-JSON o ya consumida: ignorar */
                }
            });
            await navegar();
            await page.waitForResponse(esApiProductos, { timeout: timeoutMs }).catch(() => null);
            await page.waitForTimeout(1500); // margen para XHR adicionales
            crudos = capturas.flatMap((c) => cfg.parse(c));
        }

        const productos = crudos.map((p) => {
            let url = p.url || (p.slug ? `${cfg.baseUrl}/${p.slug}/p` : '');
            if (url && !url.startsWith('http')) url = cfg.baseUrl + (url.startsWith('/') ? url : `/${url}`);
            return { ...p, url, supermercado: cfg.nombre };
        });

        return { mercado: cfg.nombre, query, productos, mejor: mejorPrecio(productos, query) };
    } finally {
        await browser.close();
    }
}

// CLI rápido:  node src/precio-referencia.js "coca cola" jumbo
// (comparación robusta en Windows y POSIX vía pathToFileURL)
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
    const [, , query, mercado] = process.argv;
    if (!query) {
        console.error('Uso: node src/precio-referencia.js "<producto>" [jumbo|santaisabel|unimarc|tottus|lider]');
        process.exit(1);
    }
    buscarPrecioReferencia(query, { mercado: mercado || 'jumbo' })
        .then((r) => console.log(JSON.stringify(r, null, 2)))
        .catch((e) => {
            console.error('Error:', e.message);
            process.exit(1);
        });
}
