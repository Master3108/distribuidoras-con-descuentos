# APIs de Supermercados — Hallazgos (jun 2026)

Investigación sobre cómo extraer precios de referencia de los supermercados
chilenos, para enriquecer datazos y calcular el % de ahorro real.

## Resumen

**Ninguno ofrece API pública oficial.** Todos sirven el shell SPA a `curl` y
bloquean bots. Los datos viajan por APIs internas / SSR que dispara el navegador.
La vía robusta (y que vence el anti-bot) es **abrir la búsqueda en un navegador
real (con stealth) e interceptar el XHR de productos, o leer el `__NEXT_DATA__`**.

## Estado por supermercado — los 5 funcionan ✅

| Supermercado | Stack | Fuente real de productos | Método |
|---|---|---|---|
| **Jumbo** (Cencosud) | BFF propio | `https://bff.jumbo.cl/catalog/plp` | XHR (URL directa) |
| **Santa Isabel** (Cencosud) | BFF propio | `https://bff.santaisabel.cl/catalog/plp` | XHR (URL directa) |
| **Unimarc** (SMU) | BFF propio | `bff-unimarc-ecommerce.unimarc.cl/catalog/product/search` | XHR + warmup; ruta `/search?q=<con-guiones>` |
| **Tottus** (Falabella) | Next.js SSR | `__NEXT_DATA__` → `props.pageProps.results` en **www.tottus.cl** | SSR + stealth + buscador |
| **Líder** (Walmart) | PerimeterX + GraphQL | `super.lider.cl/orchestra/graphql/search` | stealth + buscador (anti-bot) |

### Notas por tienda
- **VTEX clásico está MUERTO**: `/api/catalog_system/pub/products/search`
  responde 404 / 410 / 403. No usarlo.
- **Cencosud (Jumbo/Santa Isabel)** migró de VTEX a un BFF propio con JSON rico:
  `price`, `listPrice`, `ppumPrice` (precio por litro/kg), `stock` y
  `promotions[]` (ofertas "2x$2990", "6x$2700").
- **Unimarc**: ruta de búsqueda `/search?q=<termino-con-guiones>` (espacios → `-`).
  API BFF con `availableProducts[]` / `notAvailableProducts[]`; precios como
  strings ("$1.690"), `ppum` ("$1.690 x litro") y `promotion` ("2 x $2.000").
  Conviene un **warmup** en la home para cookies.
- **Tottus**: usar **www.tottus.cl** (el supermercado), NO `tottus.falabella.com`
  (catálogo general de Falabella sin alimentos). Productos en `__NEXT_DATA__`
  (`props.pageProps.results`), con `prices[]` (`internetPrice`/`normalPrice`,
  flag `crossed`) y `pum` (precio/unidad). Tras Akamai: warmup + buscar por el
  **buscador** con stealth devuelve el SSR con datos. Espacios como `+`.
- **Líder**: protegido con **PerimeterX** (captcha "Robot or human / press-and-hold").
  Se pasa con **stealth + warmup + buscador**; en este entorno fue consistente,
  pero PX es probabilístico. Marcado `requiereAntiBot: true`: si te bloquea,
  configura `BRD_BROWSER_WS` (Bright Data Scraping Browser) y el módulo se conecta
  a ese navegador gestionado. API GraphQL: `orchestra/graphql/search`; items en
  `data.search.searchResult.itemStacks[].itemsV2`.

### Anti-bot (stealth + Bright Data)
El módulo usa **playwright-extra + puppeteer-extra-plugin-stealth** globalmente
(evade PerimeterX/Akamai; no afecta a los sitios sin protección). Para tiendas con
anti-bot comercial, si defines la variable de entorno **`BRD_BROWSER_WS`** con el
endpoint del Bright Data Scraping Browser, el fetcher se conecta vía CDP a ese
navegador gestionado (proxies residenciales + solver), que resuelve los muros de
forma confiable a escala.

## Implementación

Módulo: [`scrapening-ofertas/src/precio-referencia.js`](../scrapening-ofertas/src/precio-referencia.js)

```bash
# CLI rápido (jumbo | santaisabel | unimarc | tottus | lider)
node src/precio-referencia.js "coca cola 1.5" jumbo
node src/precio-referencia.js "leche descremada" unimarc
node src/precio-referencia.js "coca cola" tottus
node src/precio-referencia.js "leche" lider
```

```js
import { buscarPrecioReferencia } from './src/precio-referencia.js';

const r = await buscarPrecioReferencia('mantequilla soprole', { mercado: 'jumbo' });
// r.mejor → { nombre, marca, precio, precioLista, ahorroPct,
//             precioPorUnidad, unidadMedida, promo, imagen, url, supermercado }
```

### Integración con el pipeline de datazos
En el Módulo 2/3 (enriquecimiento), tras extraer el nombre del producto del
video, llamar a `buscarPrecioReferencia(nombre)` para obtener `precio_supermercado`
real y calcular `ahorro_porcentaje` de forma confiable (en vez de depender solo
de lo que Claude Vision detecte en el video).

## Pendiente / mejoras
- Para uso a escala/producción de **Líder** (y Tottus si Akamai se pone duro),
  conectar Bright Data Scraping Browser vía `BRD_BROWSER_WS` (más confiable que
  el stealth local, que puede toparse con el captcha de PerimeterX).
- Cachear resultados por término para no golpear los sitios repetidamente.

## Conclusión
**Los 5 supermercados funcionan**: Jumbo, Santa Isabel, Unimarc, Tottus y Líder,
todos devolviendo catálogo de supermercado real (precio, precio/unidad y, donde
aplica, promociones). Jumbo/Santa Isabel/Unimarc son los más estables (sin
anti-bot duro); Tottus y Líder dependen de stealth y, ante bloqueos, de Bright
Data.
